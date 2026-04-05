"""Shared test fixtures for ShiftScope tests."""

from __future__ import annotations

import pytest

from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule


class AlwaysFireRule(Rule):
    """Rule that always produces a finding."""

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
    """Rule that never produces a finding."""

    rule_id = "never-fire"
    severity = Severity.WARNING

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return None


class StubAnalyzer(Analyzer):
    """Minimal analyzer for testing."""

    name = "stub-analyzer"
    version = "0.1.0"
    description = "A stub analyzer for testing."

    def __init__(self, rules: list[Rule] | None = None):
        self._rules = rules if rules is not None else [AlwaysFireRule(), NeverFireRule()]

    def analyze(self, input_path: str, **kwargs) -> Report:
        context = {"input_path": input_path, **kwargs}
        findings = self.run_rules(context)
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata=kwargs if kwargs else {},
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)


@pytest.fixture
def stub_analyzer() -> StubAnalyzer:
    return StubAnalyzer()


@pytest.fixture
def registry_with_stub() -> AnalyzerRegistry:
    reg = AnalyzerRegistry()
    reg.register(StubAnalyzer())
    return reg
