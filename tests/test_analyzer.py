"""Tests for Analyzer ABC and AnalyzerRegistry."""

from __future__ import annotations

import pytest

from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Report
from tests.stubs import StubAnalyzer


class TestAnalyzerABC:
    def test_cannot_instantiate_abstract_analyzer(self):
        with pytest.raises(TypeError):
            Analyzer()

    def test_concrete_analyzer_attributes(self):
        a = StubAnalyzer()
        assert a.name == "stub-analyzer"
        assert a.version == "0.1.0"
        assert a.description == "A stub analyzer for testing."

    def test_analyze_returns_report(self):
        a = StubAnalyzer()
        report = a.analyze("test.yaml")
        assert isinstance(report, Report)
        assert report.analyzer_name == "stub-analyzer"
        assert report.source == "test.yaml"

    def test_analyze_runs_rules(self):
        a = StubAnalyzer()
        report = a.analyze("test.yaml")
        assert len(report.findings) == 1
        assert report.findings[0].rule_id == "always-fire"

    def test_list_rules(self):
        a = StubAnalyzer()
        rules = a.list_rules()
        assert len(rules) == 2
        assert rules[0].rule_id == "always-fire"
        assert rules[1].rule_id == "never-fire"


class TestAnalyzerRegistry:
    def test_register_and_get(self):
        registry = AnalyzerRegistry()
        analyzer = StubAnalyzer()
        registry.register(analyzer)
        assert registry.get("stub-analyzer") is analyzer

    def test_get_unknown_raises(self):
        registry = AnalyzerRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_all(self, registry_with_stub):
        all_analyzers = registry_with_stub.list_all()
        assert len(all_analyzers) == 1
        assert all_analyzers[0].name == "stub-analyzer"

    def test_list_all_empty(self):
        registry = AnalyzerRegistry()
        assert registry.list_all() == []

    def test_register_duplicate_overwrites(self):
        registry = AnalyzerRegistry()
        a1 = StubAnalyzer()
        a2 = StubAnalyzer()
        registry.register(a1)
        registry.register(a2)
        assert registry.get("stub-analyzer") is a2
        assert len(registry.list_all()) == 1

    def test_discover_returns_empty_errors_when_no_plugins(self):
        registry = AnalyzerRegistry()
        errors = registry.discover(group="shiftscope.test.nonexistent")
        assert errors == []
        assert registry.list_all() == []


class TestRunRulesHelper:
    def test_run_rules_collects_findings(self, stub_analyzer):
        findings = stub_analyzer.run_rules({"input_path": "test.yaml"})
        assert len(findings) == 1
        assert findings[0].rule_id == "always-fire"

    def test_run_rules_empty_context(self, stub_analyzer):
        findings = stub_analyzer.run_rules({})
        assert len(findings) == 1
