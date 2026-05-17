"""project-brain-mcp entry point.

By default runs the MCP server over stdio. Pass --http (or set
PROJECT_BRAIN_TRANSPORT=sse) to expose the same server over
HTTP/SSE for clients like ChatGPT Desktop that don't host stdio.
"""

from __future__ import annotations

import asyncio
import os
import sys

from .server import app


def _is_http_mode() -> bool:
    """Return True if the caller requested SSE transport.

    CLI flags `--http` / `--sse` and env var
    `PROJECT_BRAIN_TRANSPORT=sse` (case-insensitive) all map to SSE.
    """
    if any(a in {"--http", "--sse"} for a in sys.argv[1:]):
        return True
    return os.environ.get("PROJECT_BRAIN_TRANSPORT", "").lower() == "sse"


def main() -> None:
    if _is_http_mode():
        port_str = os.environ.get("PROJECT_BRAIN_SSE_PORT", "8787")
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError(f"port out of range: {port}")
        except ValueError as e:
            print(
                f"FATAL: invalid PROJECT_BRAIN_SSE_PORT={port_str!r} ({e})",
                file=sys.stderr,
            )
            sys.exit(2)
        # FastMCP.run(transport=...) reads host/port from app.settings
        # rather than accepting them as kwargs, so configure first.
        app.settings.host = "127.0.0.1"
        app.settings.port = port
        app.run(transport="sse")
    else:
        asyncio.run(app.run_stdio_async())


if __name__ == "__main__":
    main()
