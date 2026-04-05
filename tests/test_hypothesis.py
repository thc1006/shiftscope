"""Property-based tests using Hypothesis for core models and renderers."""

from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from shiftscope.core.models import Finding, Report, Severity
from shiftscope.render.json_renderer import render_json
from shiftscope.render.markdown_renderer import render_markdown
from shiftscope.render.sarif_renderer import render_sarif

severity_st = st.sampled_from(list(Severity))
non_empty_text = st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",)))

finding_st = st.builds(
    Finding,
    rule_id=non_empty_text,
    severity=severity_st,
    title=non_empty_text,
    detail=non_empty_text,
    evidence=non_empty_text,
    recommendation=non_empty_text,
)

report_st = st.builds(
    Report,
    analyzer_name=non_empty_text,
    analyzer_version=st.just("0.1.0"),
    source=non_empty_text,
    findings=st.lists(finding_st, min_size=0, max_size=10),
    metadata=st.just({}),
)


class TestFindingProperties:
    @given(finding=finding_st)
    @settings(max_examples=50)
    def test_finding_fields_never_empty(self, finding: Finding):
        assert len(finding.rule_id) > 0
        assert len(finding.title) > 0
        assert len(finding.evidence) > 0
        assert len(finding.recommendation) > 0
        assert finding.severity in Severity

    @given(finding=finding_st)
    @settings(max_examples=50)
    def test_finding_json_roundtrip(self, finding: Finding):
        json_str = finding.model_dump_json()
        restored = Finding.model_validate_json(json_str)
        assert restored == finding

    @given(finding=finding_st)
    @settings(max_examples=50)
    def test_finding_is_frozen(self, finding: Finding):
        try:
            finding.rule_id = "mutated"
            raise AssertionError("Should not be mutable")
        except Exception:
            pass


class TestReportProperties:
    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_findings_count(self, report: Report):
        assert len(report.findings) == len(report.model_dump()["findings"])

    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_json_roundtrip(self, report: Report):
        json_str = report.model_dump_json(indent=2)
        restored = Report.model_validate_json(json_str)
        assert restored.analyzer_name == report.analyzer_name
        assert len(restored.findings) == len(report.findings)

    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_is_frozen(self, report: Report):
        try:
            report.analyzer_name = "mutated"
            raise AssertionError("Should not be mutable")
        except Exception:
            pass


class TestRendererProperties:
    @given(report=report_st)
    @settings(max_examples=30)
    def test_json_renderer_always_valid_json(self, report: Report):
        output = render_json(report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert "findings" in parsed

    @given(report=report_st)
    @settings(max_examples=30)
    def test_markdown_renderer_never_crashes(self, report: Report):
        md = render_markdown(report)
        assert isinstance(md, str)
        assert len(md) > 0

    @given(report=report_st)
    @settings(max_examples=30)
    def test_markdown_contains_analyzer_name(self, report: Report):
        md = render_markdown(report)
        assert report.analyzer_name in md

    @given(report=report_st)
    @settings(max_examples=30)
    def test_sarif_renderer_always_valid(self, report: Report):
        output = render_sarif(report)
        parsed = json.loads(output)
        assert parsed["version"] == "2.1.0"
        assert len(parsed["runs"]) == 1
        assert len(parsed["runs"][0]["results"]) == len(report.findings)

    @given(report=report_st)
    @settings(max_examples=30)
    def test_sarif_severity_mapping(self, report: Report):
        parsed = json.loads(render_sarif(report))
        for result in parsed["runs"][0]["results"]:
            assert result["level"] in ("error", "warning", "note")
