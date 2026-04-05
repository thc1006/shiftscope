"""MCP discovery (.well-known/mcp/server.json) and A2A Agent Card generation.

Enables AI agents to discover ShiftScope and its available analyzers
via standardized metadata endpoints.
"""

from __future__ import annotations

from typing import Any

from shiftscope import __version__
from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.mcp.bridge import build_mcp_tools

MCP_SPEC_VERSION = "2025-11-25"
A2A_SPEC_VERSION = "1.0"


def build_server_metadata(registry: AnalyzerRegistry) -> dict[str, Any]:
    """Build .well-known/mcp/server.json metadata.

    Follows the emerging MCP discovery standard (SEP-1649, SEP-1960).
    This metadata allows AI agents and MCP clients to discover
    ShiftScope's capabilities without manual configuration.
    """
    tools = build_mcp_tools(registry)

    return {
        "name": "ShiftScope",
        "version": __version__,
        "spec_version": MCP_SPEC_VERSION,
        "description": "Migration intelligence for cloud-native infrastructure API transitions.",
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
            }
            for t in tools
        ],
        "transports": ["streamable-http", "stdio"],
        "auth": {
            "type": "none",
            "note": "No authentication required for local/dev usage.",
        },
        "repository": "https://github.com/thc1006/shiftscope",
        "license": "Apache-2.0",
    }


def build_agent_card(registry: AnalyzerRegistry) -> dict[str, Any]:
    """Build an A2A (Agent-to-Agent) Agent Card.

    The Agent Card advertises ShiftScope as a callable agent
    for multi-agent orchestration via Google's A2A protocol.
    """
    analyzers = registry.list_all()

    return {
        "name": "ShiftScope",
        "version": __version__,
        "description": (
            "Pluggable migration intelligence SDK for Kubernetes infrastructure "
            "API transitions. Provides semantic risk analysis, implementation "
            "matching, and structured findings for Gateway API, DRA, Helm 4, "
            "telco intent, and agent readiness migrations."
        ),
        "url": "https://github.com/thc1006/shiftscope",
        "protocols": {
            "mcp": {"spec_version": MCP_SPEC_VERSION},
            "a2a": {"spec_version": A2A_SPEC_VERSION},
        },
        "capabilities": [
            {
                "name": a.name,
                "description": a.description,
                "version": a.version,
                "rules_count": len(a.list_rules()),
            }
            for a in analyzers
        ],
        "input_types": [
            "kubernetes-yaml",
            "network-intent-json",
            "helm-chart-dir",
            "agent-config-json",
        ],
        "output_types": ["shiftscope-report-json", "markdown"],
        "authentication": "none",
    }
