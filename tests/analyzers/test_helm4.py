"""Tests for Helm 4 readiness analyzer — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from shiftscope.core.models import Report, Severity

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
SAMPLE_CHART = EXAMPLES_DIR / "helm-sample-app"


@pytest.fixture
def analyzer():
    from analyzers.helm4.analyzer import Helm4ReadinessAnalyzer

    return Helm4ReadinessAnalyzer()


class TestChartParser:
    def test_parse_sample_chart(self):
        from analyzers.helm4.parser import parse_chart

        chart = parse_chart(str(SAMPLE_CHART))
        assert chart["api_version"] == "v2"
        assert chart["name"] == "sample-app"

    def test_parse_missing_chart_yaml(self, tmp_path):
        from analyzers.helm4.parser import parse_chart

        with pytest.raises(FileNotFoundError):
            parse_chart(str(tmp_path))


class TestChartRules:
    def test_api_v2_detected(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-chart-api-v2")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "",
            "helmignore": "",
            "values_text": "",
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.INFO

    def test_go_template_heavy(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-go-template-heavy")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": '{{- include "helpers" . }}',
            "helmignore": "",
            "values_text": "",
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING

    def test_no_go_template_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-go-template-heavy")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "simple: value",
            "helmignore": "",
            "values_text": "",
        }
        assert rule.evaluate(ctx) is None

    def test_helmignore_parity(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-helmignore-parity")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "",
            "helmignore": "**/*.bak\n/temp",
            "values_text": "",
        }
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_values_transform_with_global(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-values-transform")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "",
            "helmignore": "",
            "values_text": "global:\n  imageRegistry: docker.io\n",
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "global" in finding.evidence

    def test_values_transform_with_subchart_override(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-values-transform")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "",
            "helmignore": "",
            "values_text": "redis:\n  enabled: true\n  nameOverride: my-redis\n",
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "subchart-style" in finding.evidence

    def test_values_transform_no_match(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "helm-values-transform")
        ctx = {
            "api_version": "v2",
            "name": "test",
            "templates_content": "",
            "helmignore": "",
            "values_text": "image:\n  repository: nginx\n  tag: stable\n",
        }
        assert rule.evaluate(ctx) is None


class TestHelm4Analyzer:
    def test_analyze_sample_chart(self, analyzer):
        report = analyzer.analyze(str(SAMPLE_CHART))
        assert isinstance(report, Report)
        assert report.analyzer_name == "helm4-readiness"
        assert len(report.findings) >= 2  # at least api-v2 + go-template or helmignore

    def test_analyze_finding_has_chart_api_v2(self, analyzer):
        report = analyzer.analyze(str(SAMPLE_CHART))
        rule_ids = {f.rule_id for f in report.findings}
        assert "helm-chart-api-v2" in rule_ids

    def test_list_rules_count(self, analyzer):
        rules = analyzer.list_rules()
        assert len(rules) >= 5

    def test_json_roundtrip(self, analyzer):
        report = analyzer.analyze(str(SAMPLE_CHART))
        restored = Report.model_validate_json(report.model_dump_json())
        assert len(restored.findings) == len(report.findings)
