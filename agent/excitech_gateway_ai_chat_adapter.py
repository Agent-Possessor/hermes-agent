"""OpenAI-shaped adapter for Excitech AI Gateway `/v1/ai/chat`.

Hermes keeps its own main loop (prompting, tool handling, retries, session
state), while this adapter lets the transport hop to Excitech's orchestration
endpoint and normalize the reply back into a chat-completions-like shape.
"""

from __future__ import annotations

import json
import logging
import os
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


def _normalize_messages(messages: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(messages, list):
        return normalized
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").strip() or "user"
        normalized.append(
            {
                "role": role,
                "content": _coerce_text_content(message.get("content")),
                "name": message.get("name"),
                "tool_call_id": message.get("tool_call_id"),
                "tool_calls": message.get("tool_calls"),
            }
        )
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


def _render_tool_hints(tools: Any) -> str:
    if not isinstance(tools, list) or not tools:
        return ""

    serialized = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        serialized.append(
            {
                "type": tool.get("type"),
                "function": tool.get("function"),
            }
        )
    if not serialized:
        return ""

    return (
        "Available Hermes tools:\n"
        f"{json.dumps(serialized, ensure_ascii=False, indent=2)}\n\n"
        "If you need a tool, emit DSML tool markup that Hermes can parse.\n"
        "Format example:\n"
        "<||DSML||tool_calls>\n"
        "<||DSML||invoke name=\"tool_name\">\n"
        "<||DSML||parameter name=\"arg\" string=\"true\">value</||DSML||parameter>\n"
        "</||DSML||invoke>\n"
        "</||DSML||tool_calls>"
    )


def _render_gateway_tool_guidance() -> str:
    return (
        "Excitech Gateway tool guidance:\n"
        "- Use news.search for fresh headlines, company news, earnings, market-moving stories, or other news-specific requests.\n"
        "- Use websearch.search for broader public web evidence, verification, or current facts outside news.\n"
        "- Keep tool arguments minimal and only call a tool when external evidence is needed.\n"
        "- If the answer is self-contained, respond directly without tools."
    )


def _render_transcript(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "user").strip().upper()
        content = str(message.get("content") or "").strip()
        name = str(message.get("name") or "").strip()
        tool_call_id = str(message.get("tool_call_id") or "").strip()
        header_parts = [role]
        if name:
            header_parts.append(f"name={name}")
        if tool_call_id:
            header_parts.append(f"tool_call_id={tool_call_id}")
        lines.append(f"[{' '.join(header_parts)}]")
        if content:
            lines.append(content)
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            lines.append("tool_calls:")
            lines.append(json.dumps(tool_calls, ensure_ascii=False, indent=2))
        lines.append("")
    return "\n".join(lines).strip()


def _build_input_text(messages: list[dict[str, Any]], tools: Any) -> str:
    last_user = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user = str(message.get("content") or "").strip()
            if last_user:
                break

    sections: list[str] = []
    if last_user:
        sections.append(last_user)
    tool_hints = _render_tool_hints(tools)
    if tool_hints:
        sections.append(tool_hints)
    sections.append(_render_gateway_tool_guidance())
    return "\n\n".join(section for section in sections if section).strip()


def _resolve_endpoint(base_url: str, *, stream: bool) -> str:
    base = str(base_url or "").rstrip("/")
    if not base:
        gateway_root = os.getenv(
            "EXCITECH_GATEWAY_API_URL", "https://api-ai-kita.excitech.id"
        ).strip().rstrip("/")
        base = f"{gateway_root}/v1/openai"

    for suffix in ("/chat/completions", "/ai/chat/stream", "/ai/chat", "/openai"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    if base.endswith("/v1"):
        prefix = base
    elif "/v1/" not in base and not base.endswith("/v1"):
        prefix = base.rstrip("/") + "/v1"
    else:
        prefix = base.rstrip("/")

    return f"{prefix}/ai/chat/stream" if stream else f"{prefix}/ai/chat"


def _default_gateway_agent(model: str, configured_agent: str) -> str:
    configured = str(configured_agent or "").strip()
    if configured:
        return configured
    model_norm = str(model or "").strip().lower()
    if "reasoning" in model_norm:
        return "analyst"
    if "coder" in model_norm or "code" in model_norm:
        return "developer"
    return "assistant"


def _normalize_provider_policy(value: Any) -> Optional[dict[str, Any]]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except Exception:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _normalize_chat_response(payload: dict[str, Any], *, fallback_model: str) -> SimpleNamespace:
    envelope = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(envelope, dict):
        envelope = {}
    output = envelope.get("output") if isinstance(envelope.get("output"), dict) else {}
    routing = envelope.get("routing") if isinstance(envelope.get("routing"), dict) else None
    memory = envelope.get("memory") if isinstance(envelope.get("memory"), dict) else None
    request_id = str(payload.get("request_id") or envelope.get("request_id") or "")

    selected_model = ""
    if routing:
        selected_model = str(routing.get("selected_model") or "").strip()
    model_name = selected_model or fallback_model

    gateway_meta = {
        "request_id": request_id or None,
        "domain": envelope.get("domain"),
        "agent": envelope.get("agent"),
        "session_id": envelope.get("session_id"),
        "routing": routing,
        "memory": memory,
        "response_mode": output.get("response_mode"),
        "degraded_reason": output.get("degraded_reason"),
        "quality_tier": output.get("quality_tier"),
        "provider": routing.get("selected_provider") if routing else None,
        "model": model_name or None,
    }

    content = output.get("content")
    parsed_tool_calls = None
    if isinstance(content, str) and content:
        from agent.chat_completion_helpers import _extract_dsml_tool_calls

        content, extracted_tool_calls = _extract_dsml_tool_calls(content)
        if extracted_tool_calls:
            parsed_tool_calls = extracted_tool_calls

    normalized_message = SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=parsed_tool_calls,
        refusal=None,
        reasoning=None,
        reasoning_content=None,
        model_extra={"excitech_gateway": gateway_meta},
    )

    return SimpleNamespace(
        id=request_id or f"aichat_gateway_{int(time.time() * 1000)}",
        object="chat.completion",
        created=int(time.time()),
        model=model_name,
        choices=[
            SimpleNamespace(
                index=0,
                message=normalized_message,
                finish_reason="tool_calls" if parsed_tool_calls else "stop",
            )
        ],
        usage=_normalize_usage(payload.get("usage") or envelope.get("usage")),
    )


def _make_stream_chunk(
    *,
    model: str,
    chunk_id: str,
    content: Optional[str] = None,
    tool_calls: Optional[list[Any]] = None,
    finish_reason: Optional[str] = None,
    usage: Optional[SimpleNamespace] = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        id=chunk_id,
        object="chat.completion.chunk",
        created=int(time.time()),
        model=model,
        choices=[SimpleNamespace(index=0, delta=delta, finish_reason=finish_reason)],
        usage=usage,
    )


class _ExcitechGatewayAIChatCompletions:
    def __init__(self, owner: "ExcitechGatewayAIChatClient") -> None:
        self._owner = owner

    def create(self, **kwargs):
        stream = bool(kwargs.get("stream"))
        payload = self._owner._build_payload(kwargs)
        response = self._owner._post_chat(payload, fallback_model=str(kwargs.get("model") or ""))
        if not stream:
            return response
        return self._owner._stream_from_response(response)


class _ExcitechGatewayAIChatNamespace:
    def __init__(self, owner: "ExcitechGatewayAIChatClient") -> None:
        self.completions = _ExcitechGatewayAIChatCompletions(owner)


class ExcitechGatewayAIChatClient:
    """OpenAI-client-compatible facade backed by `/v1/ai/chat`."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_headers: Optional[dict[str, str]] = None,
        timeout: Any = None,
        http_client: Optional[httpx.Client] = None,
        agent_ref: Any = None,
        gateway_domain: str = "",
        gateway_agent: str = "",
        provider_policy: Any = None,
        **_: Any,
    ) -> None:
        self.api_key = api_key
        self.base_url = str(base_url or "").rstrip("/")
        self.default_headers = dict(default_headers or {})
        self.timeout = timeout if timeout is not None else 90.0
        self.agent_ref = agent_ref
        self.gateway_domain = str(gateway_domain or "").strip() or os.getenv("EXCITECH_GATEWAY_DOMAIN", "").strip() or "general"
        self.gateway_agent = str(gateway_agent or "").strip() or os.getenv("EXCITECH_GATEWAY_AGENT", "").strip()
        self.provider_policy = _normalize_provider_policy(provider_policy) or _normalize_provider_policy(os.getenv("EXCITECH_GATEWAY_PROVIDER_POLICY", ""))
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(timeout=self.timeout)
        self.chat = _ExcitechGatewayAIChatNamespace(self)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.default_headers)
        if self.api_key and "X-AI-API-Key" not in headers:
            headers["X-AI-API-Key"] = self.api_key
        return headers

    def _build_payload(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        normalized_messages = _normalize_messages(kwargs.get("messages"))
        extra_body = kwargs.get("extra_body") if isinstance(kwargs.get("extra_body"), dict) else {}
        model_name = str(kwargs.get("model") or "")
        payload: dict[str, Any] = {
            "domain": str(extra_body.get("domain") or extra_body.get("excitech_gateway_domain") or self.gateway_domain or "general"),
            "agent": str(extra_body.get("agent") or extra_body.get("excitech_gateway_agent") or _default_gateway_agent(model_name, self.gateway_agent)),
            "session_id": str(
                extra_body.get("session_id")
                or getattr(self.agent_ref, "session_id", "")
                or f"hermes-{int(time.time())}"
            ),
            "input": {
                "type": "text",
                "content": _build_input_text(normalized_messages, kwargs.get("tools")),
            },
            "options": {
                "stream": False,
            },
        }

        temperature = kwargs.get("temperature")
        if temperature is not None:
            payload["options"]["temperature"] = temperature
        max_tokens = kwargs.get("max_tokens")
        if max_tokens is None:
            max_tokens = kwargs.get("max_completion_tokens")
        if max_tokens is not None:
            payload["options"]["max_tokens"] = max_tokens

        provider_policy = (
            _normalize_provider_policy(extra_body.get("provider_policy"))
            or _normalize_provider_policy(extra_body.get("excitech_gateway_provider_policy"))
            or self.provider_policy
        )
        if provider_policy:
            payload["provider_policy"] = provider_policy
        return payload

    def _post_chat(self, payload: dict[str, Any], *, fallback_model: str) -> SimpleNamespace:
        url = _resolve_endpoint(self.base_url, stream=False)
        resp = self._http_client.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        try:
            body = resp.json()
        except json.JSONDecodeError as exc:
            logger.warning("excitech-gateway ai-chat returned non-JSON response: %s", exc)
            raise RuntimeError(f"Excitech gateway ai-chat returned invalid JSON: {exc}") from exc
        if isinstance(body, dict) and body.get("success") is False:
            message = str(body.get("message") or "Excitech gateway ai-chat failed")
            raise RuntimeError(message)
        return _normalize_chat_response(body if isinstance(body, dict) else {}, fallback_model=fallback_model)

    def _stream_from_response(self, response: SimpleNamespace) -> Iterable[SimpleNamespace]:
        choice = response.choices[0] if response.choices else SimpleNamespace(message=SimpleNamespace(content=None), finish_reason="stop")
        message = getattr(choice, "message", SimpleNamespace(content=None))
        content = getattr(message, "content", None)
        tool_calls = getattr(message, "tool_calls", None)
        finish_reason = getattr(choice, "finish_reason", None) or "stop"
        chunk_id = str(getattr(response, "id", "") or f"aichat_gateway_{int(time.time() * 1000)}")
        model = str(getattr(response, "model", "") or "")
        usage = getattr(response, "usage", None)

        def _iter():
            if isinstance(content, str) and content:
                yield _make_stream_chunk(
                    model=model,
                    chunk_id=chunk_id,
                    content=content,
                    tool_calls=None,
                    finish_reason=None,
                    usage=None,
                )
            if tool_calls:
                streamed_tool_calls = []
                for index, tool_call in enumerate(tool_calls):
                    function = getattr(tool_call, "function", None)
                    streamed_tool_calls.append(
                        SimpleNamespace(
                            index=index,
                            id=getattr(tool_call, "id", "") or "",
                            type=getattr(tool_call, "type", "function") or "function",
                            function=SimpleNamespace(
                                name=getattr(function, "name", "") or "",
                                arguments=getattr(function, "arguments", "") or "",
                            ),
                        )
                    )
                yield _make_stream_chunk(
                    model=model,
                    chunk_id=chunk_id,
                    content=None,
                    tool_calls=streamed_tool_calls,
                    finish_reason=None,
                    usage=None,
                )
            yield _make_stream_chunk(
                model=model,
                chunk_id=chunk_id,
                content=None,
                tool_calls=None,
                finish_reason=finish_reason,
                usage=usage,
            )

        return _iter()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()
