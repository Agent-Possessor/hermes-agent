"""Excitech AI Gateway web search + content extraction provider.

Routes web_search and web_extract tool calls through the internal
Excitech AI Gateway instead of calling external search APIs directly.

Endpoints used:
  POST /v1/search/web          — web search (Serper/Tavily/Brave/Exa via gateway)
  POST /v1/scrapper/extract-text — content extraction from URL

Auth env var:
    EXCITECH_GATEWAY_API_KEY=ak_...

Base URL override (optional, gateway root only — same var used by the LLM
provider plugin; each plugin appends its own path suffix in code):
    EXCITECH_GATEWAY_API_URL=https://api-ai-kita.excitech.id

Config (in ~/.hermes/config.yaml):
    web:
      search_backend: "excitech-gateway"
      extract_backend: "excitech-gateway"
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_DEFAULT_GATEWAY_ROOT = "https://api-ai-kita.excitech.id"
_TIMEOUT = 30.0


def _gateway_root() -> str:
    return os.getenv("EXCITECH_GATEWAY_API_URL", _DEFAULT_GATEWAY_ROOT).strip().rstrip("/")


def _search_endpoint() -> str:
    return f"{_gateway_root()}/v1/search/web"


def _extract_endpoint() -> str:
    return f"{_gateway_root()}/v1/scrapper/extract-text"


def _api_key() -> str:
    return os.getenv("EXCITECH_GATEWAY_API_KEY", "").strip()


def _auth_headers() -> dict:
    key = _api_key()
    if not key:
        return {}
    # ai-gateway uses X-AI-API-Key header, not Authorization: Bearer
    return {"X-AI-API-Key": key}


class ExcitechGatewayWebSearchProvider(WebSearchProvider):
    """Search and extract via Excitech AI Gateway.

    The gateway selects the best available search provider internally
    (Serper, Tavily, Brave, Exa, LangSearch) based on its admin config.
    """

    @property
    def name(self) -> str:
        return "excitech-gateway"

    @property
    def display_name(self) -> str:
        return "Excitech AI Gateway"

    def is_available(self) -> bool:
        return bool(_api_key())

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """POST /v1/search/web → normalized search result dict."""
        if not _api_key():
            return {"success": False, "error": "EXCITECH_GATEWAY_API_KEY is not set"}

        try:
            from tools.interrupt import is_interrupted
            if is_interrupted():
                return {"success": False, "error": "Interrupted"}
        except ImportError:
            pass

        payload = {"query": query, "limit": max(1, min(int(limit), 20))}

        try:
            resp = httpx.post(
                _search_endpoint(),
                json=payload,
                headers={**_auth_headers(), "Content-Type": "application/json"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("excitech-gateway search HTTP error: %s", exc)
            return {"success": False, "error": f"Gateway search error: {exc.response.status_code}"}
        except Exception as exc:
            logger.warning("excitech-gateway search error: %s", exc)
            return {"success": False, "error": f"Gateway search failed: {exc}"}

        # Response shape: {"status": "OK", "data": {"provider": "...", "query": "...", "items": [...]}}
        data = body.get("data", {})
        raw_items = data.get("items", [])

        web_results = []
        for i, item in enumerate(raw_items):
            web_results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", "") or item.get("description", ""),
                "position": i + 1,
            })

        return {"success": True, "data": {"web": web_results}}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """POST /v1/scrapper/extract-text for each URL → list of content dicts."""
        if not _api_key():
            return [{"url": u, "title": "", "content": "", "error": "EXCITECH_GATEWAY_API_KEY is not set"} for u in urls]

        results: List[Dict[str, Any]] = []

        for url in urls:
            try:
                from tools.interrupt import is_interrupted
                if is_interrupted():
                    results.append({"url": url, "title": "", "content": "", "error": "Interrupted"})
                    continue
            except ImportError:
                pass

            try:
                resp = httpx.post(
                    _extract_endpoint(),
                    json={"url": url, "max_chars": kwargs.get("max_chars", 8000)},
                    headers={**_auth_headers(), "Content-Type": "application/json"},
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                body = resp.json()
                data = body.get("data", {})
                text = data.get("text", "")
                results.append({
                    "url": data.get("url", url),
                    "title": "",
                    "content": text,
                    "raw_content": text,
                    "metadata": {"sourceURL": data.get("url", url)},
                })
            except httpx.HTTPStatusError as exc:
                logger.warning("excitech-gateway extract HTTP error url=%s: %s", url, exc)
                results.append({"url": url, "title": "", "content": "", "error": f"Gateway extract error: {exc.response.status_code}"})
            except Exception as exc:
                logger.warning("excitech-gateway extract error url=%s: %s", url, exc)
                results.append({"url": url, "title": "", "content": "", "error": f"Gateway extract failed: {exc}"})

        return results

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Excitech AI Gateway",
            "badge": "internal",
            "tag": "Web search and extraction via internal Excitech AI Gateway.",
            "env_vars": [
                {
                    "key": "EXCITECH_GATEWAY_API_KEY",
                    "prompt": "Excitech Gateway API key (ak_...)",
                    "url": f"{_gateway_root()}/",
                },
            ],
        }
