"""Tests for MCP bridge — TDD RED phase.

MCP is an optional dependency, so tests verify the bridge construction
and tool registration logic without requiring a running MCP server.
"""

from __future__ import annotations

import pytest

from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule
from shiftscope.mcp.bridge import build_mcp_tools, MCPBridgeError


# --- Stub analyzer ---

class StubMCPRule(Rule):
    rule_id = "mcp-test"
    severity = Severity.INFO

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return Finding(
            rule_id=self.rule_id, severity=self.severity,
            title="MCP test", detail="d", evidence="e", recommendation="r",
        )


class StubMCPAnalyzer(Analyzer):
    name = "mcp-stub"
    version = "0.1.0"
    description = "Stub for MCP testing."

    def __init__(self):
        self._rules = [StubMCPRule()]

    def analyze(self, input_path: str, **kwargs) -> Report:
        findings = self.run_rules({"input_path": input_path})
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)


class TestBuildMCPTools:
    def test_build_returns_tool_definitions(self):
        registry = AnalyzerRegistry()
        registry.register(StubMCPAnalyzer())
        tools = build_mcp_tools(registry)
        assert len(tools) >= 1

    def test_tool_names_include_analyzer(self):
        registry = AnalyzerRegistry()
        registry.register(StubMCPAnalyzer())
        tools = build_mcp_tools(registry)
        tool_names = [t["name"] for t in tools]
        assert any("mcp-stub" in name or "mcp_stub" in name for name in tool_names)

    def test_tool_has_callable(self):
        registry = AnalyzerRegistry()
        registry.register(StubMCPAnalyzer())
        tools = build_mcp_tools(registry)
        for tool in tools:
            assert callable(tool["fn"])

    def test_analyze_tool_produces_json(self, tmp_path):
        registry = AnalyzerRegistry()
        registry.register(StubMCPAnalyzer())
        tools = build_mcp_tools(registry)

        input_file = tmp_path / "test.yaml"
        input_file.write_text("test\n")

        analyze_tool = next(t for t in tools if "analyze" in t["name"])
        result = analyze_tool["fn"](str(input_file))
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert "findings" in parsed

    def test_empty_registry(self):
        registry = AnalyzerRegistry()
        tools = build_mcp_tools(registry)
        assert tools == []
