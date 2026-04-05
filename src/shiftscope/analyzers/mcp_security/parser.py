"""MCP config parser — extracts server definitions from MCP config files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_mcp_config(path: str | Path) -> dict[str, Any]:
    """Parse an MCP config file (mcp.json, claude_desktop_config.json, etc.)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    # Normalize: support both top-level mcpServers and flat format
    servers: dict[str, Any] = {}
    if "mcpServers" in data:
        servers = data["mcpServers"]
    elif "servers" in data:
        servers = data["servers"]
    else:
        # Treat entire object as a single server if it has "command"
        if "command" in data:
            servers = {"default": data}

    return {"servers": servers, "raw": data}
