from __future__ import annotations

def test_create_openai_client_uses_ai_chat_mode_for_excitech_gateway(monkeypatch):
    captured = {}

    class FakeAIChatClient:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        "agent.excitech_gateway_ai_chat_adapter.ExcitechGatewayAIChatClient",
        FakeAIChatClient,
    )
    monkeypatch.setenv("EXCITECH_GATEWAY_MODE", "ai-chat")
    monkeypatch.setenv("EXCITECH_GATEWAY_DOMAIN", "general")
    monkeypatch.setenv("EXCITECH_GATEWAY_AGENT", "assistant")

    from run_agent import AIAgent

    agent = AIAgent.__new__(AIAgent)
    agent.provider = "excitech-gateway"
    agent.model = "general-main"
    agent.base_url = "https://api-ai-kita.excitech.id/v1/openai"
    agent.session_id = "sess_001"
    agent._client_kwargs = {}
    agent._build_keepalive_http_client = lambda *_args, **_kwargs: None
    agent._client_log_context = lambda: "provider=excitech-gateway"

    client_kwargs = {
        "api_key": "ak_test",
        "base_url": "https://api-ai-kita.excitech.id/v1/openai",
    }
    client = agent._create_openai_client(client_kwargs, reason="test", shared=False)

    assert isinstance(client, FakeAIChatClient)
    assert captured["kwargs"]["gateway_domain"] == "general"
    assert captured["kwargs"]["gateway_agent"] == "assistant"
    assert captured["kwargs"]["agent_ref"] is agent
    assert captured["kwargs"]["base_url"] == "https://api-ai-kita.excitech.id/v1/openai"


def test_create_openai_client_defaults_to_openai_proxy_for_excitech_gateway(monkeypatch):
    captured = {}

    class FakeProxyClient:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        "agent.excitech_gateway_adapter.ExcitechGatewayClient",
        FakeProxyClient,
    )
    monkeypatch.delenv("EXCITECH_GATEWAY_MODE", raising=False)

    from run_agent import AIAgent

    agent = AIAgent.__new__(AIAgent)
    agent.provider = "excitech-gateway"
    agent.model = "general-main"
    agent.base_url = "https://api-ai-kita.excitech.id/v1/openai"
    agent._client_kwargs = {}
    agent._build_keepalive_http_client = lambda *_args, **_kwargs: None
    agent._client_log_context = lambda: "provider=excitech-gateway"

    client_kwargs = {
        "api_key": "ak_test",
        "base_url": "https://api-ai-kita.excitech.id/v1/openai",
    }
    client = agent._create_openai_client(client_kwargs, reason="test", shared=False)

    assert isinstance(client, FakeProxyClient)
    assert captured["kwargs"]["base_url"] == "https://api-ai-kita.excitech.id/v1/openai"
