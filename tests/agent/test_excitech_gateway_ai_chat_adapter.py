from __future__ import annotations

from types import SimpleNamespace

from agent.excitech_gateway_ai_chat_adapter import ExcitechGatewayAIChatClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHTTPClient:
    def __init__(self, payload):
        self.payload = payload
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
        return _FakeResponse(self.payload)


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
    assert request["url"] == "https://api-ai-kita.excitech.id/v1/ai/chat"
    assert request["headers"]["X-AI-API-Key"] == "ak_test"
    assert request["json"]["domain"] == "general"
    assert request["json"]["agent"] == "analyst"
    assert request["json"]["session_id"] == "sess_abc"
    assert request["json"]["options"]["stream"] is False
    assert request["json"]["options"]["max_tokens"] == 512
    assert request["json"]["input"]["content"].startswith("cek harga BTC hari ini")
    assert "Available Hermes tools:" in request["json"]["input"]["content"]
    assert "Hermes conversation transcript:" not in request["json"]["input"]["content"]
    assert "Anda adalah Hermes." not in request["json"]["input"]["content"]

    assert response.id == "req_123"
    assert response.model == "stepfun-ai/step-3.5-flash"
    assert response.choices[0].message.content == "BTC saat ini sekitar ..."
    gateway_meta = response.choices[0].message.model_extra["excitech_gateway"]
    assert gateway_meta["routing"]["selected_provider"] == "nvidia_nim"
    assert gateway_meta["quality_tier"] == "standard"


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
        base_url="https://api-ai-kita.excitech.id/v1/openai",
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
        base_url="https://api-ai-kita.excitech.id/v1/openai",
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
