"""Excitech AI Gateway provider profile.

Routes all LLM calls through the internal Excitech AI Gateway
(https://api-ai-kita.excitech.id/) which handles provider routing,
fallback logic, and quota enforcement internally.

The gateway exposes an OpenAI-compatible endpoint at /v1/openai.
Auth uses X-AI-API-Key header — injected automatically via default_headers
so hermes does not need any special transport configuration.

The gateway's auto-routing selects the best backend (OpenCode Zen,
NVIDIA NIM, etc.) based on the model alias:
  general-main   → general-purpose tasks (auto-routed by gateway)
  reasoning-main → reasoning/complex tasks
  nvidia-coder   → coding tasks

Auth env var:
    EXCITECH_GATEWAY_API_KEY=ak_...

Config (in ~/.hermes/config.yaml):
    model:
      provider: excitech-gateway
      default: general-main
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

from providers import register_provider
from providers.base import ProviderProfile, _profile_user_agent

logger = logging.getLogger(__name__)


class ExcitechGatewayProfile(ProviderProfile):
    """ProviderProfile that injects X-AI-API-Key for both model listing and chat calls."""

    # Override as a property so the env var is read at request time, not at
    # module load time (which may precede .env loading).
    @property
    def default_headers(self) -> dict:
        key = os.getenv("EXCITECH_GATEWAY_API_KEY", "").strip()
        return {"X-AI-API-Key": key} if key else {}

    @default_headers.setter
    def default_headers(self, value) -> None:
        pass  # intentionally ignored — always derived from env

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        effective_base = base_url or self.base_url
        url = effective_base.rstrip("/") + "/models"
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("X-AI-API-Key", api_key)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", _profile_user_agent())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            items = data if isinstance(data, list) else data.get("data", [])
            return [m["id"] for m in items if isinstance(m, dict) and "id" in m]
        except Exception as exc:
            logger.debug("fetch_models(excitech-gateway): %s", exc)
            return None


excitech_gateway = ExcitechGatewayProfile(
    name="excitech-gateway",
    aliases=("excitech", "ai-kita", "ai_gateway"),
    env_vars=("EXCITECH_GATEWAY_API_KEY",),
    display_name="Excitech AI Gateway",
    description="Internal gateway — auto-routes to best backend, no model config needed",
    signup_url="https://api-ai-kita.excitech.id/",
    base_url="https://api-ai-kita.excitech.id/v1/openai",
    supports_vision=True,
    fallback_models=(
        "general-main",    # auto-routing (default)
        "reasoning-main",  # complex/reasoning tasks
        "nvidia-coder",    # coding tasks
    ),
)

register_provider(excitech_gateway)
