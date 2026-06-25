"""OpenAI-shaped adapter for Excitech AI Gateway.

Excitech's gateway is reachable via an OpenAI-compatible path, but for Hermes
the most reliable integration is to call it directly and normalize the response
ourselves. This avoids depending on the OpenAI SDK's SSE parser for a gateway
that already computes the full completion server-side before emitting a stream.
"""

from __future__ import annotations

import json
import logging
import time
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _coerce_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: List[str] = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    pieces.append(text)
        return "\n".join(piece for piece in pieces if piece)
    return str(content)


def _normalize_messages(messages: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(messages, list):
        return normalized
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").strip() or "user"
        content = _coerce_text_content(message.get("content"))
        normalized.append({"role": role, "content": content})
    return normalized


def _normalize_usage(usage: Any) -> Optional[SimpleNamespace]:
    if not isinstance(usage, dict):
        return None
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
    return SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _normalize_chat_response(payload: dict[str, Any], *, fallback_model: str) -> SimpleNamespace:
    choices_raw = payload.get("choices")
    if not isinstance(choices_raw, list) or not choices_raw:
        choices_raw = [{}]

    normalized_choices = []
    for idx, choice in enumerate(choices_raw):
        if not isinstance(choice, dict):
            choice = {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        normalized_message = SimpleNamespace(
            role=str(message.get("role") or "assistant"),
            content=message.get("content"),
            tool_calls=message.get("tool_calls"),
            refusal=message.get("refusal"),
            reasoning=getattr(message, "reasoning", None),
            reasoning_content=message.get("reasoning_content"),
            model_extra=message,
        )
        normalized_choices.append(
            SimpleNamespace(
                index=int(choice.get("index") or idx),
                message=normalized_message,
                finish_reason=choice.get("finish_reason"),
            )
        )

    return SimpleNamespace(
        id=str(payload.get("id") or f"chatcmpl_gateway_{int(time.time() * 1000)}"),
        object=str(payload.get("object") or "chat.completion"),
        created=int(payload.get("created") or time.time()),
        model=str(payload.get("model") or fallback_model),
        choices=normalized_choices,
        usage=_normalize_usage(payload.get("usage")),
    )


def _make_stream_chunk(
    *,
    model: str,
    chunk_id: str,
    content: Optional[str] = None,
    finish_reason: Optional[str] = None,
    usage: Optional[SimpleNamespace] = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(
        id=chunk_id,
        object="chat.completion.chunk",
        created=int(time.time()),
        model=model,
        choices=[SimpleNamespace(index=0, delta=delta, finish_reason=finish_reason)],
        usage=usage,
    )


class _ExcitechGatewayChatCompletions:
    def __init__(self, owner: "ExcitechGatewayClient") -> None:
        self._owner = owner

    def create(self, **kwargs):
        stream = bool(kwargs.get("stream"))
        payload = self._owner._build_payload(kwargs, force_stream=False)
        response = self._owner._post_chat(payload)
        if not stream:
            return response
        return self._owner._stream_from_response(response)


class _ExcitechGatewayChatNamespace:
    def __init__(self, owner: "ExcitechGatewayClient") -> None:
        self.completions = _ExcitechGatewayChatCompletions(owner)


class ExcitechGatewayClient:
    """Small OpenAI-client-compatible facade for Excitech gateway."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_headers: Optional[dict[str, str]] = None,
        timeout: Any = None,
        http_client: Optional[httpx.Client] = None,
        **_: Any,
    ) -> None:
        self.api_key = api_key
        self.base_url = str(base_url or "").rstrip("/")
        self.default_headers = dict(default_headers or {})
        self.timeout = timeout if timeout is not None else 60.0
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(timeout=self.timeout)
        self.chat = _ExcitechGatewayChatNamespace(self)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.default_headers)
        if self.api_key and "X-AI-API-Key" not in headers:
            headers["X-AI-API-Key"] = self.api_key
        return headers

    def _build_payload(self, kwargs: dict[str, Any], *, force_stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": kwargs.get("model"),
            "messages": _normalize_messages(kwargs.get("messages")),
            "stream": force_stream,
        }
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs.get("temperature")
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs.get("max_tokens")
        elif kwargs.get("max_completion_tokens") is not None:
            payload["max_tokens"] = kwargs.get("max_completion_tokens")
        # Forward optional OpenAI-ish fields for future gateway support.
        for key in ("tools", "tool_choice", "response_format"):
            if key in kwargs and kwargs.get(key) is not None:
                payload[key] = kwargs.get(key)
        extra_body = kwargs.get("extra_body")
        if isinstance(extra_body, dict):
            for key, value in extra_body.items():
                payload.setdefault(key, value)
        return payload

    def _post_chat(self, payload: dict[str, Any]) -> SimpleNamespace:
        url = f"{self.base_url}/chat/completions"
        resp = self._http_client.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        try:
            body = resp.json()
        except json.JSONDecodeError as exc:
            logger.warning("excitech-gateway returned non-JSON response: %s", exc)
            raise RuntimeError(f"Excitech gateway returned invalid JSON: {exc}") from exc
        return _normalize_chat_response(body, fallback_model=str(payload.get("model") or ""))

    def _stream_from_response(self, response: SimpleNamespace) -> Iterable[SimpleNamespace]:
        choice = response.choices[0] if response.choices else SimpleNamespace(message=SimpleNamespace(content=None), finish_reason="stop")
        message = getattr(choice, "message", SimpleNamespace(content=None))
        content = getattr(message, "content", None)
        finish_reason = getattr(choice, "finish_reason", None) or "stop"
        chunk_id = str(getattr(response, "id", "") or f"chatcmpl_gateway_{int(time.time() * 1000)}")
        model = str(getattr(response, "model", "") or "")
        usage = getattr(response, "usage", None)

        def _iter():
            if isinstance(content, str) and content:
                yield _make_stream_chunk(
                    model=model,
                    chunk_id=chunk_id,
                    content=content,
                    finish_reason=None,
                    usage=None,
                )
            yield _make_stream_chunk(
                model=model,
                chunk_id=chunk_id,
                content=None,
                finish_reason=finish_reason,
                usage=usage,
            )

        return _iter()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

