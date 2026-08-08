"""Excitech AI Gateway provider profile.

Routes all LLM calls through the internal Excitech AI Gateway
(https://api-ai-kita.excitech.id/) which handles provider routing,
fallback logic, and quota enforcement internally.

The gateway is called through its orchestrated AI chat endpoint at
``/v1/ai/chat``.

Auth uses X-AI-API-Key header — injected automatically via default_headers
so hermes does not need any special transport configuration.

The gateway's auto-routing selects the best backend (OpenCode Zen,
NVIDIA NIM, etc.) based on the model alias:
  general-main   → general-purpose tasks (auto-routed by gateway)
  reasoning-main → reasoning/complex tasks
  nvidia-coder   → coding tasks

Auth env var:
    EXCITECH_GATEWAY_API_KEY=ak_...

Base URL override (optional, gateway root only — /v1/ai/chat is appended in code):
    EXCITECH_GATEWAY_API_URL=https://api-ai-kita.excitech.id

Config (in ~/.hermes/config.yaml):
    model:
      provider: excitech-gateway
      default: general-main
      excitech_gateway_domain: general
      excitech_gateway_agent: assistant
"""

from __future__ import annotations

import os

from providers import register_provider
from providers.base import ProviderProfile

_DEFAULT_GATEWAY_ROOT = "https://api-ai-kita.excitech.id"


def _gateway_root() -> str:
    return os.getenv("EXCITECH_GATEWAY_API_URL", _DEFAULT_GATEWAY_ROOT).strip().rstrip("/")


def _gateway_base_url() -> str:
    return f"{_gateway_root()}/v1/ai/chat"


class ExcitechGatewayProfile(ProviderProfile):
    """Provider profile for the Excitech orchestration endpoint."""

    # Override as a property so the env var is read at request time, not at
    # module load time (which may precede .env loading).
    @property
    def default_headers(self) -> dict:
        key = os.getenv("EXCITECH_GATEWAY_API_KEY", "").strip()
        return {"X-AI-API-Key": key} if key else {}

    @default_headers.setter
    def default_headers(self, value) -> None:
        pass  # intentionally ignored — always derived from env

    # Same deferred-read trick as default_headers: base_url is read at
    # request time so EXCITECH_GATEWAY_API_URL can override it.
    @property
    def base_url(self) -> str:
        return _gateway_base_url()

    @base_url.setter
    def base_url(self, value) -> None:
        pass  # intentionally ignored — always derived from env

    def fetch_models(self, **_) -> None:
        """The orchestration API has no model-catalog endpoint."""
        return None


excitech_gateway = ExcitechGatewayProfile(
    name="excitech-gateway",
    aliases=("excitech", "ai-kita", "ai_gateway"),
    env_vars=("EXCITECH_GATEWAY_API_KEY",),
    display_name="Excitech AI Gateway",
    description="Internal AI chat orchestration with automatic routing",
    signup_url=f"{_gateway_root()}/",
    base_url=_gateway_base_url(),
    supports_health_check=False,
    supports_vision=True,
    fallback_models=(
        "general-main",    # auto-routing (default)
        "reasoning-main",  # complex/reasoning tasks
        "nvidia-coder",    # coding tasks
    ),
)

register_provider(excitech_gateway)
