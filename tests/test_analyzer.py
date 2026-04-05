"""Tests for Analyzer ABC and AnalyzerRegistry — TDD RED phase."""

from __future__ import annotations

import pytest

from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule


# --- Test fixtures: concrete implementations for testing ---

class AlwaysFireRule(Rule):
    rule_id = "always-fire"
    severity = Severity.INFO

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Always fires",
            detail="This rule always produces a finding.",
            evidence="N/A",
            recommendation="No action needed.",
        )


class NeverFireRule(Rule):
    rule_id = "never-fire"
    severity = Severity.WARNING

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return None


class StubAnalyzer(Analyzer):
    name = "stub-analyzer"
    version = "0.1.0"
    description = "A stub analyzer for testing."

    def __init__(self):
        self._rules = [AlwaysFireRule(), NeverFireRule()]

    def analyze(self, input_path: str, **kwargs) -> Report:
        context = {"input_path": input_path, **kwargs}
        findings = self.run_rules(context)
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)


# --- Tests ---

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
        assert len(report.findings) == 1  # AlwaysFireRule fires, NeverFireRule doesn't
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
        retrieved = registry.get("stub-analyzer")
        assert retrieved is analyzer

    def test_get_unknown_raises(self):
        registry = AnalyzerRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_all(self):
        registry = AnalyzerRegistry()
        a = StubAnalyzer()
        registry.register(a)
        all_analyzers = registry.list_all()
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
    def test_run_rules_collects_findings(self):
        a = StubAnalyzer()
        findings = a.run_rules({"input_path": "test.yaml"})
        assert len(findings) == 1
        assert findings[0].rule_id == "always-fire"

    def test_run_rules_empty_context(self):
        a = StubAnalyzer()
        findings = a.run_rules({})
        assert len(findings) == 1  # AlwaysFireRule always applies
