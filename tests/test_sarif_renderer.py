"""Tests for SARIF 2.1.0 renderer."""

from __future__ import annotations

import json

from shiftscope.core.models import Finding, Report, Severity
from shiftscope.render.sarif_renderer import render_sarif


def _sample_report() -> Report:
    return Report(
        analyzer_name="gateway-api",
        analyzer_version="0.2.0",
        source="manifests/ingress.yaml",
        findings=[
            Finding(
                rule_id="gw-behavior-regex-prefix",
                severity=Severity.CRITICAL,
                title="Regex behavior change",
                detail="ingress-nginx regex is prefix-based and case-insensitive.",
                evidence="test: path='/[A-Z]{3}'",
                recommendation="Add '.*' suffix and '(?i)' flag.",
            ),
            Finding(
                rule_id="gw-annotation-enable-cors",
                severity=Severity.WARNING,
                title="CORS annotation detected",
                detail="Partial Gateway API coverage.",
                evidence="enable-cors=true",
                recommendation="Use HTTPRoute CORS filter.",
            ),
            Finding(
                rule_id="gw-behavior-path-normalization",
                severity=Severity.INFO,
                title="Path normalization may differ",
                detail="Varies per implementation.",
                evidence="1 path(s)",
                recommendation="Verify docs.",
            ),
        ],
    )


class TestSARIFSchema:
    def test_valid_json(self):
        report = _sample_report()
        sarif_str = render_sarif(report)
        sarif = json.loads(sarif_str)
        assert isinstance(sarif, dict)

    def test_sarif_version(self):
        sarif = json.loads(render_sarif(_sample_report()))
        assert sarif["version"] == "2.1.0"

    def test_has_schema_uri(self):
        sarif = json.loads(render_sarif(_sample_report()))
        assert "$schema" in sarif
        assert "sarif-schema-2.1.0" in sarif["$schema"]

    def test_has_runs(self):
        sarif = json.loads(render_sarif(_sample_report()))
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1

    def test_tool_driver(self):
        sarif = json.loads(render_sarif(_sample_report()))
        driver = sarif["runs"][0]["tool"]["driver"]
        assert driver["name"] == "ShiftScope"
        assert "version" in driver
        assert "rules" in driver

    def test_rules_match_findings(self):
        sarif = json.loads(render_sarif(_sample_report()))
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}
        assert "gw-behavior-regex-prefix" in rule_ids
        assert "gw-annotation-enable-cors" in rule_ids
        assert len(rules) == 3

    def test_results_count(self):
        sarif = json.loads(render_sarif(_sample_report()))
        results = sarif["runs"][0]["results"]
        assert len(results) == 3


class TestSeverityMapping:
    def test_critical_maps_to_error(self):
        sarif = json.loads(render_sarif(_sample_report()))
        results = sarif["runs"][0]["results"]
        critical = next(r for r in results if r["ruleId"] == "gw-behavior-regex-prefix")
        assert critical["level"] == "error"

    def test_warning_maps_to_warning(self):
        sarif = json.loads(render_sarif(_sample_report()))
        results = sarif["runs"][0]["results"]
        warning = next(r for r in results if r["ruleId"] == "gw-annotation-enable-cors")
        assert warning["level"] == "warning"

    def test_info_maps_to_note(self):
        sarif = json.loads(render_sarif(_sample_report()))
        results = sarif["runs"][0]["results"]
        info = next(r for r in results if r["ruleId"] == "gw-behavior-path-normalization")
        assert info["level"] == "note"


class TestSARIFContent:
    def test_result_has_message(self):
        sarif = json.loads(render_sarif(_sample_report()))
        result = sarif["runs"][0]["results"][0]
        assert "message" in result
        assert "text" in result["message"]

    def test_result_has_location(self):
        sarif = json.loads(render_sarif(_sample_report()))
        result = sarif["runs"][0]["results"][0]
        assert "locations" in result
        loc = result["locations"][0]["physicalLocation"]["artifactLocation"]
        assert loc["uri"] == "manifests/ingress.yaml"

    def test_rule_has_description(self):
        sarif = json.loads(render_sarif(_sample_report()))
        rule = sarif["runs"][0]["tool"]["driver"]["rules"][0]
        assert "shortDescription" in rule
        assert "text" in rule["shortDescription"]

    def test_empty_report(self):
        report = Report(
            analyzer_name="test",
            analyzer_version="0.1.0",
            source="empty.yaml",
            findings=[],
        )
        sarif = json.loads(render_sarif(report))
        assert sarif["runs"][0]["results"] == []
        assert sarif["runs"][0]["tool"]["driver"]["rules"] == []

    def test_json_roundtrip(self):
        sarif_str = render_sarif(_sample_report())
        restored = json.loads(sarif_str)
        re_serialized = json.dumps(restored, indent=2)
        assert json.loads(re_serialized) == restored
