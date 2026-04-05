"""Tests for MCP bridge."""

from __future__ import annotations

import json

from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.mcp.bridge import build_mcp_tools
from tests.stubs import StubAnalyzer


class TestBuildMCPTools:
    def test_build_returns_tool_definitions(self, registry_with_stub):
        tools = build_mcp_tools(registry_with_stub)
        assert len(tools) == 1

    def test_tool_names_include_analyzer(self, registry_with_stub):
        tools = build_mcp_tools(registry_with_stub)
        assert tools[0]["name"] == "analyze_stub_analyzer"

    def test_tool_has_callable(self, registry_with_stub):
        tools = build_mcp_tools(registry_with_stub)
        for tool in tools:
            assert callable(tool["fn"])

    def test_tool_has_description(self, registry_with_stub):
        tools = build_mcp_tools(registry_with_stub)
        assert "stub-analyzer" in tools[0]["description"]

    def test_analyze_tool_produces_valid_json(self, tmp_path, registry_with_stub):
        tools = build_mcp_tools(registry_with_stub)
        input_file = tmp_path / "test.yaml"
        input_file.write_text("test\n")

        result = tools[0]["fn"](str(input_file))
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["analyzer_name"] == "stub-analyzer"
        assert "findings" in parsed
        assert len(parsed["findings"]) == 1

    def test_empty_registry(self):
        registry = AnalyzerRegistry()
        tools = build_mcp_tools(registry)
        assert tools == []

    def test_multiple_analyzers(self):
        registry = AnalyzerRegistry()
        a1 = StubAnalyzer()
        # Create a second stub with different name
        a2 = StubAnalyzer()
        a2.name = "second-stub"
        registry.register(a1)
        registry.register(a2)
        tools = build_mcp_tools(registry)
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert "analyze_stub_analyzer" in names
        assert "analyze_second_stub" in names
