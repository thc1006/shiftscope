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
non_empty_text = st.text(
    min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))
)

finding_st = st.builds(
    Finding,
    rule_id=non_empty_text,
    severity=severity_st,
    title=non_empty_text,
    detail=non_empty_text,
    evidence=non_empty_text,
    recommendation=non_empty_text,
)

# Strategy allowing empty strings (for renderer edge cases)
any_text = st.text(max_size=100, alphabet=st.characters(blacklist_categories=("Cs",)))

finding_with_empties_st = st.builds(
    Finding,
    rule_id=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
    severity=severity_st,
    title=any_text,
    detail=any_text,
    evidence=any_text,
    recommendation=any_text,
)

report_with_empties_st = st.builds(
    Report,
    analyzer_name=st.text(
        min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))
    ),
    analyzer_version=st.just("0.1.0"),
    source=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
    findings=st.lists(finding_with_empties_st, min_size=0, max_size=5),
    metadata=st.builds(dict),
)

report_st = st.builds(
    Report,
    analyzer_name=non_empty_text,
    analyzer_version=st.just("0.1.0"),
    source=non_empty_text,
    findings=st.lists(finding_st, min_size=0, max_size=10),
    metadata=st.builds(dict),
)


class TestFindingProperties:
    @given(finding=finding_st)
    @settings(max_examples=50)
    def test_finding_fields_never_empty(self, finding: Finding):
        assert len(finding.rule_id) > 0
        assert len(finding.title) > 0
        assert len(finding.detail) > 0
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
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            finding.rule_id = "mutated"


class TestReportProperties:
    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_findings_count_matches_json(self, report: Report):
        json_data = json.loads(report.model_dump_json())
        assert len(json_data["findings"]) == len(report.findings)
        for i, finding in enumerate(report.findings):
            assert json_data["findings"][i]["rule_id"] == finding.rule_id

    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_json_roundtrip(self, report: Report):
        json_str = report.model_dump_json(indent=2)
        restored = Report.model_validate_json(json_str)
        assert restored == report

    @given(report=report_st)
    @settings(max_examples=30)
    def test_report_is_frozen(self, report: Report):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            report.analyzer_name = "mutated"


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


class TestRendererEdgeCases:
    @given(report=report_with_empties_st)
    @settings(max_examples=30)
    def test_json_handles_empty_strings(self, report: Report):
        output = render_json(report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    @given(report=report_with_empties_st)
    @settings(max_examples=30)
    def test_markdown_handles_empty_strings(self, report: Report):
        md = render_markdown(report)
        assert isinstance(md, str)

    @given(report=report_with_empties_st)
    @settings(max_examples=30)
    def test_sarif_handles_empty_strings(self, report: Report):
        output = render_sarif(report)
        parsed = json.loads(output)
        assert parsed["version"] == "2.1.0"
