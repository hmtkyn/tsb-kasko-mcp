"""ASGI application exposing the MCP server over streamable HTTP.

Hosted MCP clients such as ChatGPT connectors reach the server over HTTP rather
than stdio. This module provides the application object those deployments expect,
so the server can be started with any ASGI runner::

    uvicorn tsb_kasko.asgi:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os

from .server import mcp

MCP_PATH = os.getenv("TSB_KASKO_MCP_PATH", "/mcp")

app = mcp.http_app(path=MCP_PATH, stateless_http=True)
"""Starlette application serving the MCP endpoint at :data:`MCP_PATH`."""
