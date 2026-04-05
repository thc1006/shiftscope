"""Tests for telco intent provenance analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from shiftscope.core.models import Report, Severity

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
SAMPLE_INTENT = EXAMPLES_DIR / "telco-intent.json"


@pytest.fixture
def analyzer():
    from shiftscope.analyzers.telco_intent.analyzer import TelcoIntentAnalyzer

    return TelcoIntentAnalyzer()


class TestTelcoRules:
    def test_gitops_target_validation(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "telco-gitops-target")
        ctx = {"gitops_target": "flux", "region": "eu-central"}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "flux" in finding.evidence.lower() or "Flux" in finding.detail

    def test_gitops_argocd_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "telco-gitops-target")
        ctx = {"gitops_target": "argocd", "region": "eu-central"}
        assert rule.evaluate(ctx) is None

    def test_provenance_review_required(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "telco-provenance-review")
        ctx = {"require_ipv4": True, "has_hydration": True}
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_no_hydration_no_provenance_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "telco-provenance-review")
        ctx = {"require_ipv4": False, "has_hydration": False}
        assert rule.evaluate(ctx) is None

    def test_southbound_contract_only(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "telco-southbound-contract")
        ctx = {"southbound_target": "sdc"}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.INFO


class TestTelcoIntentAnalyzer:
    def test_analyze_sample_intent(self, analyzer):
        report = analyzer.analyze(str(SAMPLE_INTENT))
        assert isinstance(report, Report)
        assert report.analyzer_name == "telco-intent"
        assert len(report.findings) >= 1

    def test_list_rules_count(self, analyzer):
        assert len(analyzer.list_rules()) >= 3

    def test_json_roundtrip(self, analyzer):
        report = analyzer.analyze(str(SAMPLE_INTENT))
        restored = Report.model_validate_json(report.model_dump_json())
        assert len(restored.findings) == len(report.findings)
