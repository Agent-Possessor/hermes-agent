from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent.excitech_gateway_ai_chat_adapter import (
    AsyncExcitechGatewayAIChatClient,
    ExcitechGatewayError,
    ExcitechGatewayAIChatClient,
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHTTPClient:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.calls = []

    def post(self, url, *, headers=None, json=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return _FakeResponse(self.payload, self.status_code)


def test_ai_chat_adapter_surfaces_gateway_candidate_attempts():
    http_client = _FakeHTTPClient(
        {
            "success": False,
            "message": "Agent completion failed",
            "error": {
                "details": {
                    "attempts": [
                        {
                            "provider": "nvidia_nim",
                            "model": "stepfun-ai/step-3.7-flash",
                            "error": "provider status=400 code=BAD_REQUEST",
                        },
                        {
                            "provider": "openrouter",
                            "model": "anthropic/claude-sonnet-4",
                            "error": "provider status=402 code=PAYMENT_REQUIRED",
                        },
                    ]
                }
            },
        },
        status_code=502,
    )
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/agent/chat/completions",
        http_client=http_client,
    )

    with pytest.raises(ExcitechGatewayError) as raised:
        client.chat.completions.create(
            model="reasoning-main",
            messages=[{"role": "user", "content": "analyze"}],
        )

    assert raised.value.status_code == 502
    assert "nvidia_nim/stepfun-ai/step-3.7-flash" in str(raised.value)
    assert "openrouter/anthropic/claude-sonnet-4" in str(raised.value)


def test_ai_chat_adapter_maps_payload_and_response_metadata():
    payload = {
        "success": True,
        "request_id": "req_123",
        "data": {
            "domain": "general",
            "agent": "analyst",
            "session_id": "sess_abc",
            "routing": {
                "selected_provider": "nvidia_nim",
                "selected_model": "stepfun-ai/step-3.5-flash",
            },
            "output": {
                "content": "BTC saat ini sekitar ...",
                "response_mode": "normal",
                "degraded_reason": "",
                "quality_tier": "standard",
            },
            "memory": {"loaded": True, "saved": True},
        },
    }
    http_client = _FakeHTTPClient(payload)
    agent_ref = SimpleNamespace(session_id="sess_abc")
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        # A legacy saved proxy base URL is migrated to the stateless endpoint.
        base_url="https://api-ai-kita.excitech.id/v1/openai",
        http_client=http_client,
        agent_ref=agent_ref,
        gateway_domain="general",
        gateway_agent="analyst",
    )

    response = client.chat.completions.create(
        model="reasoning-main",
        messages=[
            {"role": "system", "content": "Anda adalah Hermes."},
            {"role": "user", "content": "cek harga BTC hari ini"},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "parameters": {"type": "object"},
                },
            }
        ],
        temperature=0.2,
        max_tokens=512,
    )

    assert http_client.calls, "adapter should issue one HTTP request"
    request = http_client.calls[0]
    assert request["url"] == "https://api-ai-kita.excitech.id/v1/agent/chat/completions"
    assert request["headers"]["X-AI-API-Key"] == "ak_test"
    assert request["json"]["routing"]["domain"] == "general"
    assert request["json"]["routing"]["agent"] == "analyst"
    assert request["json"]["routing"]["original_user_input"] == "cek harga BTC hari ini"
    assert request["json"]["stream"] is False
    assert request["json"]["max_tokens"] == 512
    assert request["json"]["messages"][0] == {
        "role": "system",
        "content": "Anda adalah Hermes.",
        "name": None,
        "tool_call_id": None,
        "tool_calls": None,
    }
    assert request["json"]["tools"][0]["function"]["name"] == "web_search"

    assert response.id == "req_123"
    assert response.model == "stepfun-ai/step-3.5-flash"
    assert response.choices[0].message.content == "BTC saat ini sekitar ..."
    gateway_meta = response.choices[0].message.model_extra["excitech_gateway"]
    assert gateway_meta["routing"]["selected_provider"] == "nvidia_nim"
    assert gateway_meta["quality_tier"] == "standard"


def test_ai_chat_adapter_preserves_native_full_tool_loop():
    payload = {
        "success": True,
        "data": {"output": {"content": "Tool result accepted."}},
    }
    http_client = _FakeHTTPClient(payload)
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/ai/chat",
        http_client=http_client,
    )

    client.chat.completions.create(
        model="general-main",
        messages=[
            {"role": "system", "content": "Follow the Hermes system policy."},
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "inspect the repository"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    SimpleNamespace(
                        id="call_1",
                        type="function",
                        function=SimpleNamespace(
                            name="terminal",
                            arguments='{"command":"git status --short"}',
                        ),
                    )
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "terminal",
                "content": " M agent.py",
            },
        ],
    )

    request = http_client.calls[0]
    assert request["url"] == "https://api-ai-kita.excitech.id/v1/agent/chat/completions"
    messages = request["json"]["messages"]
    assert [message["role"] for message in messages] == [
        "system", "user", "assistant", "user", "assistant", "tool"
    ]
    assert messages[-2]["tool_calls"][0]["function"]["name"] == "terminal"
    assert messages[-1]["tool_call_id"] == "call_1"
    assert messages[-1]["content"] == " M agent.py"
    assert request["json"]["routing"]["original_user_input"] == "inspect the repository"


def test_ai_chat_adapter_keeps_recovery_in_messages_but_routes_on_original_user():
    payload = {
        "id": "req_native",
        "object": "chat.completion",
        "model": "fallback-model",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Final answer"},
            "finish_reason": "stop",
        }],
        "gateway": {"provider": "fallback", "fallback_used": True},
    }
    http_client = _FakeHTTPClient(payload)
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/agent/chat/completions",
        http_client=http_client,
    )

    response = client.chat.completions.create(
        model="general-main",
        messages=[
            {"role": "user", "content": "analyze Menu Kita"},
            {"role": "assistant", "content": None, "tool_calls": []},
            {"role": "tool", "tool_call_id": "call_1", "content": "evidence"},
            {
                "role": "user",
                "content": "You just executed tool calls but returned an empty response. Please continue.",
            },
        ],
    )

    request = http_client.calls[0]["json"]
    assert request["routing"]["original_user_input"] == "analyze Menu Kita"
    assert request["messages"][-1]["content"].startswith("You just executed")
    assert response.choices[0].message.content == "Final answer"
    assert response.choices[0].message.model_extra["excitech_gateway"]["fallback_used"] is True


def test_ai_chat_adapter_preserves_multimodal_message_parts():
    http_client = _FakeHTTPClient({
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "described"},
            "finish_reason": "stop",
        }],
    })
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/agent/chat/completions",
        http_client=http_client,
    )
    parts = [
        {"type": "text", "text": "describe this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
    ]

    client.chat.completions.create(
        model="general-main",
        messages=[{"role": "user", "content": parts}],
    )

    request = http_client.calls[0]["json"]
    assert request["messages"][0]["content"] == parts
    assert request["routing"]["original_user_input"] == "describe this"


def test_ai_chat_adapter_promotes_dsml_markup_into_tool_calls():
    payload = {
        "success": True,
        "request_id": "req_dsml",
        "data": {
            "routing": {
                "selected_provider": "nvidia_nim",
                "selected_model": "stepfun-ai/step-3.5-flash",
            },
            "output": {
                "content": (
                    "Saya cek dulu.\n\n"
                    "<||DSML||tool_calls>\n"
                    "<||DSML||invoke name=\"terminal\">\n"
                    "<||DSML||parameter name=\"command\" string=\"true\">curl -s https://example.com</||DSML||parameter>\n"
                    "<||DSML||parameter name=\"timeout\" string=\"true\">15</||DSML||parameter>\n"
                    "</||DSML||invoke>\n"
                    "</||DSML||tool_calls>"
                ),
            },
        },
    }
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/ai/chat",
        http_client=_FakeHTTPClient(payload),
    )

    response = client.chat.completions.create(
        model="general-main",
        messages=[{"role": "user", "content": "cek harga BTC saat ini"}],
    )

    choice = response.choices[0]
    assert choice.finish_reason == "tool_calls"
    assert choice.message.content == "Saya cek dulu."
    assert choice.message.tool_calls is not None
    assert len(choice.message.tool_calls) == 1
    tool_call = choice.message.tool_calls[0]
    assert tool_call.function.name == "terminal"
    assert tool_call.function.arguments == '{"command": "curl -s https://example.com", "timeout": "15"}'


def test_ai_chat_adapter_stream_projects_tool_calls_from_dsml_response():
    payload = {
        "success": True,
        "request_id": "req_stream_dsml",
        "data": {
            "routing": {
                "selected_provider": "nvidia_nim",
                "selected_model": "stepfun-ai/step-3.5-flash",
            },
            "output": {
                "content": (
                    "<||DSML||tool_calls>\n"
                    "<||DSML||invoke name=\"web_search\">\n"
                    "<||DSML||parameter name=\"query\" string=\"true\">Bitcoin price today USD IDR</||DSML||parameter>\n"
                    "</||DSML||invoke>\n"
                    "</||DSML||tool_calls>"
                ),
            },
        },
    }
    client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/ai/chat",
        http_client=_FakeHTTPClient(payload),
    )

    chunks = list(
        client.chat.completions.create(
            model="general-main",
            messages=[{"role": "user", "content": "cek harga BTC saat ini"}],
            stream=True,
        )
    )

    assert len(chunks) == 2
    assert chunks[0].choices[0].delta.tool_calls is not None
    tool_delta = chunks[0].choices[0].delta.tool_calls[0]
    assert tool_delta.index == 0
    assert tool_delta.function.name == "web_search"
    assert tool_delta.function.arguments == '{"query": "Bitcoin price today USD IDR"}'
    assert chunks[-1].choices[0].finish_reason == "tool_calls"


def test_auxiliary_client_uses_ai_chat_adapter_for_local_gateway(monkeypatch):
    from agent import auxiliary_client

    monkeypatch.setattr(auxiliary_client, "_openai_http_client_kwargs", lambda *_args, **_kwargs: {})
    client = auxiliary_client._create_openai_client(
        api_key="ak_test",
        base_url="http://127.0.0.1:8080/v1/ai/chat",
    )

    assert isinstance(client, ExcitechGatewayAIChatClient)
    assert client.base_url == "http://127.0.0.1:8080/v1/ai/chat"


def test_async_ai_chat_adapter_preserves_async_stream_contract():
    payload = {
        "success": True,
        "request_id": "req_async",
        "data": {"output": {"content": "async response"}},
    }
    sync_client = ExcitechGatewayAIChatClient(
        api_key="ak_test",
        base_url="https://api-ai-kita.excitech.id/v1/ai/chat",
        http_client=_FakeHTTPClient(payload),
    )
    client = AsyncExcitechGatewayAIChatClient(sync_client)

    async def _collect():
        chunks = await client.chat.completions.create(
            model="general-main",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )
        return [chunk async for chunk in chunks]

    chunks = asyncio.run(_collect())
    assert chunks[0].choices[0].delta.content == "async response"
    assert chunks[-1].choices[0].finish_reason == "stop"
