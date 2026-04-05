"""Tests for MCP discovery (.well-known) and A2A Agent Card."""

from __future__ import annotations

import json

from shiftscope.core.analyzer import AnalyzerRegistry
from shiftscope.mcp.discovery import build_agent_card, build_server_metadata
from tests.stubs import StubAnalyzer


class TestMCPServerMetadata:
    """Tests for .well-known/mcp/server.json generation."""

    def test_metadata_has_required_fields(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        meta = build_server_metadata(registry)

        assert meta["name"] == "ShiftScope"
        assert "spec_version" in meta
        assert "tools" in meta
        assert isinstance(meta["tools"], list)

    def test_metadata_lists_all_tools(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        meta = build_server_metadata(registry)
        assert len(meta["tools"]) == 1
        assert meta["tools"][0]["name"] == "analyze_stub_analyzer"

    def test_metadata_includes_transport(self):
        registry = AnalyzerRegistry()
        meta = build_server_metadata(registry)
        assert "transports" in meta
        assert "streamable-http" in meta["transports"]
        assert "stdio" in meta["transports"]

    def test_metadata_json_serializable(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        meta = build_server_metadata(registry)
        json_str = json.dumps(meta, indent=2)
        restored = json.loads(json_str)
        assert restored["name"] == "ShiftScope"

    def test_metadata_empty_registry(self):
        registry = AnalyzerRegistry()
        meta = build_server_metadata(registry)
        assert meta["tools"] == []


class TestA2AAgentCard:
    """Tests for A2A Agent Card generation."""

    def test_card_has_required_fields(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        card = build_agent_card(registry)

        assert card["name"] == "ShiftScope"
        assert "description" in card
        assert "capabilities" in card
        assert "url" in card

    def test_card_capabilities_match_analyzers(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        card = build_agent_card(registry)
        assert len(card["capabilities"]) == 1
        assert card["capabilities"][0]["name"] == "stub-analyzer"

    def test_card_json_serializable(self):
        registry = AnalyzerRegistry()
        registry.register(StubAnalyzer())
        card = build_agent_card(registry)
        json_str = json.dumps(card, indent=2)
        restored = json.loads(json_str)
        assert restored["name"] == "ShiftScope"

    def test_card_includes_protocol_versions(self):
        registry = AnalyzerRegistry()
        card = build_agent_card(registry)
        assert "protocols" in card
        assert "mcp" in card["protocols"]
        assert "a2a" in card["protocols"]
