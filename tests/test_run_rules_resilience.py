"""Tests for run_rules() resilience — broken rules don't crash the analyzer."""

from __future__ import annotations

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule


class GoodRule(Rule):
    rule_id = "good-rule"
    severity = Severity.INFO

    def applies_to(self, context):
        return True

    def evaluate(self, context):
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Good",
            detail="d",
            evidence="e",
            recommendation="r",
        )


class BrokenRule(Rule):
    rule_id = "broken-rule"
    severity = Severity.CRITICAL

    def applies_to(self, context):
        return True

    def evaluate(self, context):
        raise RuntimeError("this rule is broken")


class MixedAnalyzer(Analyzer):
    name = "mixed"
    version = "0.1.0"
    description = "Has good and broken rules"

    def __init__(self):
        self._rules = [GoodRule(), BrokenRule(), GoodRule()]

    def analyze(self, input_path, **kwargs):
        findings = self.run_rules({})
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
        )

    def list_rules(self):
        return list(self._rules)


class TestRunRulesResilience:
    def test_broken_rule_does_not_crash(self):
        a = MixedAnalyzer()
        report = a.analyze("test.yaml")
        # Should have 3 findings: good + broken-error + good
        assert len(report.findings) == 3

    def test_broken_rule_produces_critical_finding(self):
        a = MixedAnalyzer()
        report = a.analyze("test.yaml")
        error_findings = [f for f in report.findings if "failed" in f.title.lower()]
        assert len(error_findings) == 1
        assert error_findings[0].severity == Severity.CRITICAL
        assert error_findings[0].rule_id == "broken-rule"

    def test_good_rules_still_produce_findings(self):
        a = MixedAnalyzer()
        report = a.analyze("test.yaml")
        good_findings = [f for f in report.findings if f.rule_id == "good-rule"]
        assert len(good_findings) == 2
