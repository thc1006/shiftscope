"""MCP Security analyzer — vulnerability detection for MCP server configurations.

Scans MCP config files (mcp.json, claude_desktop_config.json, .cursor/mcp.json)
for security vulnerabilities. Deterministic-first (no LLM required).
"""

from __future__ import annotations

from typing import Any

from shiftscope.analyzers.mcp_security.parser import parse_mcp_config
from shiftscope.analyzers.mcp_security.rules import build_rules
from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule


class MCPSecurityAnalyzer(Analyzer):
    """Scans MCP server configurations for security vulnerabilities."""

    name = "mcp-security"
    version = "0.1.0"
    description = "MCP server security vulnerability detection (OWASP ASI mapped)"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        config = parse_mcp_config(input_path)
        all_findings = []

        for server_name, server_config in config["servers"].items():
            context = {
                "server_name": server_name,
                "command": server_config.get("command", ""),
                "args": server_config.get("args", []),
                "env": server_config.get("env", {}),
                "auth": server_config.get("auth"),
            }
            all_findings.extend(self.run_rules(context))

        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=all_findings,
            metadata={"server_count": len(config["servers"])},
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)
