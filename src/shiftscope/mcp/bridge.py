"""MCP bridge — auto-generate MCP tools from registered analyzers.

Generates tool definitions that can be registered with FastMCP.
The actual MCP server creation requires the optional 'mcp' extra.
"""

from __future__ import annotations

from typing import Any

from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.render.json_renderer import render_json


class MCPBridgeError(Exception):
    """Raised when MCP bridge encounters an error."""


def build_mcp_tools(registry: AnalyzerRegistry) -> list[dict[str, Any]]:
    """Build MCP tool definitions from all registered analyzers.

    Returns a list of dicts, each with:
      - name: tool name (e.g., "analyze_gateway_api")
      - description: human-readable description
      - fn: callable(input_path: str) -> str (JSON)

    These can be registered with FastMCP via @mcp.tool() or manually.
    """
    tools: list[dict[str, Any]] = []

    for analyzer in registry.list_all():
        safe_name = analyzer.name.replace("-", "_")

        def _make_analyze_fn(a=analyzer):
            def analyze_fn(input_path: str) -> str:
                report = a.analyze(input_path)
                return render_json(report)

            return analyze_fn

        tools.append(
            {
                "name": f"analyze_{safe_name}",
                "description": f"Run {analyzer.name} migration analyzer. {analyzer.description}",
                "fn": _make_analyze_fn(),
            }
        )

    return tools


def create_mcp_server(
    registry: AnalyzerRegistry,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> Any:
    """Create a FastMCP server with tools for all registered analyzers.

    Requires the 'mcp' optional extra to be installed.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as err:
        raise MCPBridgeError(
            "MCP support requires the 'mcp' extra. Install with: pip install shiftscope[mcp]"
        ) from err

    mcp = FastMCP("ShiftScope Migration Intelligence", host=host, port=port)

    for tool_def in build_mcp_tools(registry):
        mcp.tool(name=tool_def["name"], description=tool_def["description"])(tool_def["fn"])

    return mcp
