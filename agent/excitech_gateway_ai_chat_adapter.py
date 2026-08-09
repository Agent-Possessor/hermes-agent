"""OpenAI-shaped adapter for Excitech AI Gateway agent completions.

Hermes keeps its own main loop (prompting, tool handling, retries, session
state), while this adapter delegates stateless model routing and fallback to
Excitech and normalizes the reply back into a chat-completions-like shape.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ExcitechGatewayError(RuntimeError):
    """HTTP-aware gateway failure that keeps safe provider-attempt details."""

    def __init__(self, message: str, *, status_code: int, body: Any, response: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = {"message": message, "gateway": body}
        self.response = response


def _gateway_error_message(body: Any) -> str:
    if not isinstance(body, dict):
        return "Excitech gateway request failed"
    message = str(body.get("message") or "Excitech gateway request failed").strip()
    error = body.get("error") if isinstance(body.get("error"), dict) else {}
    details = error.get("details") if isinstance(error.get("details"), dict) else {}
    attempts = details.get("attempts") if isinstance(details.get("attempts"), list) else []
    summaries: list[str] = []
    for attempt in attempts[:6]:
        if not isinstance(attempt, dict):
            continue
        provider = str(attempt.get("provider") or "unknown-provider").strip()
        model = str(attempt.get("model") or "unknown-model").strip()
        reason = " ".join(str(attempt.get("error") or "failed").split())
        summaries.append(f"{provider}/{model}: {reason[:180]}")
    if summaries:
        return f"{message} after {len(attempts)} candidate(s): " + "; ".join(summaries)
    reason = " ".join(str(details.get("reason") or "").split())
    return f"{message}: {reason[:300]}" if reason else message


_DSML_TAG_STEM = r"(?:[|｜]\s*){2}DSML(?:\s*[|｜]){2}"
_DSML_TOOL_CALLS_RE = re.compile(
    rf"<\s*{_DSML_TAG_STEM}\s*tool_calls\s*>(.*?)</\s*{_DSML_TAG_STEM}\s*tool_calls\s*>",
    flags=re.DOTALL | re.IGNORECASE,
)
_DSML_INVOKE_RE = re.compile(
    rf"<\s*{_DSML_TAG_STEM}\s*invoke\b([^>]*)>(.*?)</\s*{_DSML_TAG_STEM}\s*invoke\s*>",
    flags=re.DOTALL | re.IGNORECASE,
)
_DSML_PARAM_RE = re.compile(
    rf"<\s*{_DSML_TAG_STEM}\s*parameter\b([^>]*)>(.*?)</\s*{_DSML_TAG_STEM}\s*parameter\s*>",
    flags=re.DOTALL | re.IGNORECASE,
)
_XML_ATTR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"([^"]*)"')


def _extract_dsml_tool_calls(content: str) -> tuple[str, list[SimpleNamespace]]:
    """Convert inline DSML emitted by the gateway into Hermes tool calls."""
    if not isinstance(content, str) or "DSML" not in content.upper():
        return content, []

    parsed_calls: list[SimpleNamespace] = []
    matched_blocks = False
    for match in _DSML_TOOL_CALLS_RE.finditer(content):
        matched_blocks = True
        block = match.group(1) or ""
        for invoke_index, invoke_match in enumerate(_DSML_INVOKE_RE.finditer(block)):
            attrs = dict(_XML_ATTR_RE.findall(invoke_match.group(1) or ""))
            tool_name = (attrs.get("name") or "").strip()
            if not tool_name:
                continue

            arguments: dict[str, Any] = {}
            for param_match in _DSML_PARAM_RE.finditer(invoke_match.group(2) or ""):
                param_attrs = dict(_XML_ATTR_RE.findall(param_match.group(1) or ""))
                param_name = (param_attrs.get("name") or "").strip()
                if not param_name:
                    continue
                raw_value = (param_match.group(2) or "").strip()
                if (param_attrs.get("string") or "").strip().lower() == "true":
                    arguments[param_name] = raw_value
                    continue
                if raw_value == "":
                    arguments[param_name] = ""
                    continue
                try:
                    arguments[param_name] = json.loads(raw_value)
                except (TypeError, ValueError):
                    arguments[param_name] = raw_value

            call_id = f"dsml_{tool_name}_{invoke_index}_{uuid.uuid4().hex[:12]}"
            parsed_calls.append(
                SimpleNamespace(
                    id=call_id,
                    call_id=call_id,
                    response_item_id=None,
                    type="function",
                    extra_content=None,
                    function=SimpleNamespace(
                        name=tool_name,
                        arguments=json.dumps(arguments, ensure_ascii=False),
                    ),
                )
            )

    if not matched_blocks:
        return content, []
    cleaned = _DSML_TOOL_CALLS_RE.sub("", content)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip(), parsed_calls


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
                continue
            if item.get("type") in {"image_url", "input_image"}:
                image_value = item.get("image_url") or item.get("url")
                if isinstance(image_value, dict):
                    image_value = image_value.get("url")
                if isinstance(image_value, str) and image_value:
                    pieces.append(f"[image: {image_value}]")
                else:
                    pieces.append("[image attached]")
        return "\n".join(piece for piece in pieces if piece)
    return str(content)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump())
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return str(value)


def _normalize_messages(messages: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(messages, list):
        return normalized
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").strip() or "user"
        raw_content = message.get("content")
        content = (
            _json_safe(raw_content)
            if isinstance(raw_content, (list, dict))
            else _coerce_text_content(raw_content)
        )
        normalized.append(
            {
                "role": role,
                "content": content,
                "name": message.get("name"),
                "tool_call_id": message.get("tool_call_id"),
                "tool_calls": _json_safe(message.get("tool_calls")),
            }
        )
    return normalized


_EMPTY_TOOL_RECOVERY_PREFIX = "you just executed tool calls but returned an empty response"


def _original_user_input(messages: list[dict[str, Any]]) -> str:
    """Return the latest real user input for gateway routing.

    Hermes may append a synthetic user nudge after an empty post-tool reply.
    That nudge remains in messages for model continuity but must not become the
    gateway's routing/search intent.
    """
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        raw_content = message.get("content")
        if isinstance(raw_content, list):
            content = "\n".join(
                str(part.get("text") or "").strip()
                for part in raw_content
                if isinstance(part, dict) and part.get("type") in {"text", "input_text"}
            ).strip()
        else:
            content = str(raw_content or "").strip()
        if not content:
            continue
        if content.lower().startswith(_EMPTY_TOOL_RECOVERY_PREFIX):
            continue
        return content
    return ""


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


def _resolve_endpoint(base_url: str) -> str:
    base = str(base_url or "").rstrip("/")
    if not base:
        base = os.getenv(
            "EXCITECH_GATEWAY_API_URL", "https://api-ai-kita.excitech.id"
        ).strip().rstrip("/")

    if base.endswith("/v1/agent/chat/completions"):
        return base
    # Migrate saved orchestration/proxy URLs to the stateless agent endpoint.
    if base.endswith("/v1/ai/chat"):
        return f"{base[:-len('/ai/chat')]}/agent/chat/completions"
    if base.endswith("/v1/openai"):
        return f"{base[:-len('/openai')]}/agent/chat/completions"
    if base.endswith("/v1"):
        return f"{base}/agent/chat/completions"
    return f"{base}/v1/agent/chat/completions"


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
    # The stateless agent endpoint is OpenAI-compatible. Keep the legacy
    # /v1/ai/chat envelope parser below for rolling upgrades and old fixtures.
    if isinstance(payload.get("choices"), list):
        raw_choices = payload.get("choices") or []
        normalized_choices = []
        for index, raw_choice in enumerate(raw_choices):
            if not isinstance(raw_choice, dict):
                continue
            raw_message = raw_choice.get("message") if isinstance(raw_choice.get("message"), dict) else {}
            parsed_tool_calls = []
            for raw_call in raw_message.get("tool_calls") or []:
                if not isinstance(raw_call, dict):
                    continue
                raw_function = raw_call.get("function") if isinstance(raw_call.get("function"), dict) else {}
                parsed_tool_calls.append(
                    SimpleNamespace(
                        id=str(raw_call.get("id") or ""),
                        call_id=str(raw_call.get("id") or ""),
                        response_item_id=None,
                        type=str(raw_call.get("type") or "function"),
                        extra_content=None,
                        function=SimpleNamespace(
                            name=str(raw_function.get("name") or ""),
                            arguments=str(raw_function.get("arguments") or "{}"),
                        ),
                    )
                )
            normalized_choices.append(
                SimpleNamespace(
                    index=int(raw_choice.get("index", index)),
                    message=SimpleNamespace(
                        role=str(raw_message.get("role") or "assistant"),
                        content=raw_message.get("content"),
                        tool_calls=parsed_tool_calls or None,
                        refusal=raw_message.get("refusal"),
                        reasoning=raw_message.get("reasoning"),
                        reasoning_content=raw_message.get("reasoning_content"),
                        model_extra={"excitech_gateway": payload.get("gateway") or {}},
                    ),
                    finish_reason=raw_choice.get("finish_reason") or ("tool_calls" if parsed_tool_calls else "stop"),
                )
            )
        return SimpleNamespace(
            id=str(payload.get("id") or f"agent_gateway_{int(time.time() * 1000)}"),
            object=str(payload.get("object") or "chat.completion"),
            created=int(payload.get("created") or time.time()),
            model=str(payload.get("model") or fallback_model),
            choices=normalized_choices,
            usage=_normalize_usage(payload.get("usage")),
        )

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


class _AsyncExcitechGatewayAIChatCompletions:
    def __init__(self, owner: "AsyncExcitechGatewayAIChatClient") -> None:
        self._owner = owner

    async def create(self, **kwargs):
        result = await asyncio.to_thread(
            self._owner._sync.chat.completions.create, **kwargs
        )
        if not kwargs.get("stream"):
            return result

        async def _iterate():
            for chunk in result:
                yield chunk

        return _iterate()


class _AsyncExcitechGatewayAIChatNamespace:
    def __init__(self, owner: "AsyncExcitechGatewayAIChatClient") -> None:
        self.completions = _AsyncExcitechGatewayAIChatCompletions(owner)


class ExcitechGatewayAIChatClient:
    """OpenAI-client-compatible facade backed by agent completions."""

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
            "model": model_name or "auto",
            "messages": normalized_messages,
            "stream": False,
            "routing": {
                "domain": str(extra_body.get("domain") or extra_body.get("excitech_gateway_domain") or self.gateway_domain or "general"),
                "agent": str(extra_body.get("agent") or extra_body.get("excitech_gateway_agent") or _default_gateway_agent(model_name, self.gateway_agent)),
                "original_user_input": _original_user_input(normalized_messages),
            },
        }

        tools = _json_safe(kwargs.get("tools"))
        if isinstance(tools, list) and tools:
            payload["tools"] = tools
        if kwargs.get("tool_choice") is not None:
            payload["tool_choice"] = _json_safe(kwargs.get("tool_choice"))
        if kwargs.get("parallel_tool_calls") is not None:
            payload["parallel_tool_calls"] = bool(kwargs.get("parallel_tool_calls"))
        if isinstance(kwargs.get("response_format"), dict):
            payload["response_format"] = _json_safe(kwargs.get("response_format"))

        temperature = kwargs.get("temperature")
        if temperature is not None:
            payload["temperature"] = temperature
        max_tokens = kwargs.get("max_tokens")
        if max_tokens is None:
            max_tokens = kwargs.get("max_completion_tokens")
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        provider_policy = (
            _normalize_provider_policy(extra_body.get("provider_policy"))
            or _normalize_provider_policy(extra_body.get("excitech_gateway_provider_policy"))
            or self.provider_policy
        )
        if provider_policy:
            payload["provider_policy"] = provider_policy
        return payload

    def _post_chat(self, payload: dict[str, Any], *, fallback_model: str) -> SimpleNamespace:
        url = _resolve_endpoint(self.base_url)
        resp = self._http_client.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        try:
            body = resp.json()
        except json.JSONDecodeError as exc:
            resp.raise_for_status()
            logger.warning("excitech-gateway ai-chat returned non-JSON response: %s", exc)
            raise RuntimeError(f"Excitech gateway ai-chat returned invalid JSON: {exc}") from exc
        status_code = int(getattr(resp, "status_code", 200) or 200)
        if status_code >= 400:
            raise ExcitechGatewayError(
                _gateway_error_message(body),
                status_code=status_code,
                body=body,
                response=resp,
            )
        if isinstance(body, dict) and body.get("success") is False:
            raise ExcitechGatewayError(
                _gateway_error_message(body),
                status_code=status_code,
                body=body,
                response=resp,
            )
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
        # Hermes supplies a fresh keepalive client per provider client. Closing
        # it here is required during model switches and credential rotation so
        # sockets do not accumulate across rebuilds.
        close = getattr(self._http_client, "close", None)
        if callable(close):
            close()


class AsyncExcitechGatewayAIChatClient:
    """Async facade used by Hermes auxiliary tasks.

    The gateway endpoint is synchronous, so the blocking request is isolated
    in a worker thread while preserving the AsyncOpenAI-shaped interface.
    """

    def __init__(self, sync_client: ExcitechGatewayAIChatClient) -> None:
        self._sync = sync_client
        self.api_key = sync_client.api_key
        self.base_url = sync_client.base_url
        self.chat = _AsyncExcitechGatewayAIChatNamespace(self)

    async def close(self) -> None:
        await asyncio.to_thread(self._sync.close)

    async def aclose(self) -> None:
        await self.close()
