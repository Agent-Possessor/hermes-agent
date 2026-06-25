"""Excitech AI Gateway web search + extract plugin — bundled, auto-loaded."""

from __future__ import annotations

from plugins.web.excitech_gateway.provider import ExcitechGatewayWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(ExcitechGatewayWebSearchProvider())
