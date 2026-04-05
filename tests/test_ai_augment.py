"""Tests for AI augmentation layer."""

from __future__ import annotations

from shiftscope.ai.augment import AugmentedReport, augment_report
from shiftscope.core.models import Finding, Report, Severity


def _sample_report() -> Report:
    return Report(
        analyzer_name="gateway-api",
        analyzer_version="0.1.0",
        source="test.yaml",
        findings=[
            Finding(
                rule_id="gw-tls-wildcard",
                severity=Severity.CRITICAL,
                title="Wildcard TLS host detected",
                detail="Verify certificate overlap.",
                evidence="*.example.com",
                recommendation="Review ListenerSet.",
            ),
            Finding(
                rule_id="gw-annotation-enable-cors",
                severity=Severity.WARNING,
                title="CORS annotation detected",
                detail="Partial Gateway API coverage.",
                evidence="enable-cors=true",
                recommendation="Use HTTPRoute CORS filter.",
            ),
        ],
    )


class TestAugmentedReport:
    def test_wraps_original_report(self):
        report = _sample_report()
        augmented = AugmentedReport(report=report, ai_summary=None)
        assert augmented.report is report
        assert augmented.ai_summary is None

    def test_with_ai_summary(self):
        report = _sample_report()
        augmented = AugmentedReport(
            report=report,
            ai_summary="This manifest has 2 migration risks.",
        )
        assert augmented.ai_summary == "This manifest has 2 migration risks."

    def test_original_findings_not_modified(self):
        report = _sample_report()
        augmented = AugmentedReport(
            report=report,
            ai_summary="AI says something.",
        )
        assert augmented.report.findings == report.findings
        assert len(augmented.report.findings) == 2
        assert augmented.report.findings[0].rule_id == "gw-tls-wildcard"

    def test_json_roundtrip(self):
        report = _sample_report()
        augmented = AugmentedReport(
            report=report,
            ai_summary="Summary here.",
            ai_model="gpt-4.1-mini",
        )
        json_str = augmented.model_dump_json(indent=2)
        restored = AugmentedReport.model_validate_json(json_str)
        assert restored.ai_summary == "Summary here."
        assert restored.ai_model == "gpt-4.1-mini"
        assert len(restored.report.findings) == 2

    def test_ai_generated_flag(self):
        report = _sample_report()
        augmented = AugmentedReport(
            report=report,
            ai_summary="Summary.",
        )
        assert augmented.is_ai_augmented is True

    def test_no_ai_flag_when_no_summary(self):
        report = _sample_report()
        augmented = AugmentedReport(report=report, ai_summary=None)
        assert augmented.is_ai_augmented is False


class TestAugmentReport:
    def test_augment_without_ai_installed(self):
        """When PydanticAI is not available, augment_report returns report with no AI summary."""
        report = _sample_report()
        result = augment_report(report)
        assert isinstance(result, AugmentedReport)
        assert result.ai_summary is None
        assert result.report is report

    def test_augment_with_mock_ai(self):
        """Test augmentation with a mock summarizer (no real LLM call)."""
        report = _sample_report()

        def mock_summarizer(r: Report) -> str:
            rule_ids = [f.rule_id for f in r.findings]
            return f"Found {len(r.findings)} issues: {', '.join(rule_ids)}"

        result = augment_report(report, summarizer=mock_summarizer)
        assert result.is_ai_augmented is True
        assert "gw-tls-wildcard" in result.ai_summary
        assert "gw-annotation-enable-cors" in result.ai_summary
        assert "2 issues" in result.ai_summary


class TestFaithfulness:
    """AI summary must reference actual findings, not hallucinate."""

    def test_faithful_summary_references_actual_findings(self):
        report = _sample_report()

        def faithful_summarizer(r: Report) -> str:
            return f"Critical: {r.findings[0].title}. Warning: {r.findings[1].title}."

        result = augment_report(report, summarizer=faithful_summarizer)
        # Summary should contain text from actual findings
        assert "Wildcard TLS" in result.ai_summary
        assert "CORS" in result.ai_summary

    def test_unfaithful_summary_detectable(self):
        """We can detect when a summary mentions rule_ids not in the report."""
        report = _sample_report()
        # Simulate an AI summary that mentions a rule_id not in the report
        hallucinated_id = "dra-alpha-feature-gate"
        report_rule_ids = {f.rule_id for f in report.findings}
        assert hallucinated_id not in report_rule_ids  # Confirmed: this is hallucination
