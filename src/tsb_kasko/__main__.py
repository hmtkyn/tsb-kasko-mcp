"""Module entry point so the package can be started with ``python -m tsb_kasko``.

Running the module starts the MCP server, which is what ``uvx tsb-kasko-mcp`` and
MCP client configurations expect. Use the ``tsb-kasko`` console script for the
terminal interface.
"""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()
