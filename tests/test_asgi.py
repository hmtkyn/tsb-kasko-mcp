"""Tests for the ASGI application used by hosted MCP deployments."""

from __future__ import annotations

import importlib

import pytest


def test_app_serves_the_default_mcp_path() -> None:
    from tsb_kasko import asgi

    assert asgi.MCP_PATH == "/mcp"
    assert "/mcp" in {getattr(route, "path", None) for route in asgi.app.routes}


def test_app_is_an_asgi_callable() -> None:
    from tsb_kasko import asgi

    # Any ASGI runner calls the app as app(scope, receive, send).
    assert callable(asgi.app)


def test_mcp_path_follows_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TSB_KASKO_MCP_PATH", "/kasko")
    module = importlib.import_module("tsb_kasko.asgi")
    try:
        reloaded = importlib.reload(module)
        assert reloaded.MCP_PATH == "/kasko"
        assert "/kasko" in {getattr(route, "path", None) for route in reloaded.app.routes}
    finally:
        # Leave the module in its default state for whatever runs next.
        monkeypatch.delenv("TSB_KASKO_MCP_PATH")
        importlib.reload(module)
