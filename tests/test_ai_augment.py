"""Tests for AI augmentation layer."""

from __future__ import annotations

from unittest.mock import patch

from shiftscope.ai.augment import AugmentedReport, augment_report, check_faithfulness
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
        augmented = AugmentedReport(report=report, ai_summary="AI says something.")
        assert augmented.report.findings == report.findings
        assert len(augmented.report.findings) == 2

    def test_json_roundtrip(self):
        report = _sample_report()
        augmented = AugmentedReport(
            report=report, ai_summary="Summary here.", ai_model="gpt-4.1-mini"
        )
        json_str = augmented.model_dump_json(indent=2)
        restored = AugmentedReport.model_validate_json(json_str)
        assert restored.ai_summary == "Summary here."
        assert restored.ai_model == "gpt-4.1-mini"
        assert len(restored.report.findings) == 2

    def test_ai_generated_flag(self):
        report = _sample_report()
        augmented = AugmentedReport(report=report, ai_summary="Summary.")
        assert augmented.is_ai_augmented is True

    def test_no_ai_flag_when_no_summary(self):
        report = _sample_report()
        augmented = AugmentedReport(report=report, ai_summary=None)
        assert augmented.is_ai_augmented is False


class TestAugmentReport:
    def test_augment_without_ai_installed(self):
        """When PydanticAI is not available, returns report with no AI summary."""
        report = _sample_report()
        with patch(
            "shiftscope.ai.augment._default_pydantic_ai_summarizer",
            side_effect=ImportError("not installed"),
        ):
            result = augment_report(report)
        assert isinstance(result, AugmentedReport)
        assert result.ai_summary is None
        assert result.report is report

    def test_augment_with_mock_summarizer(self):
        report = _sample_report()

        def mock_summarizer(r: Report) -> str:
            rule_ids = [f.rule_id for f in r.findings]
            return f"Found {len(r.findings)} issues: {', '.join(rule_ids)}"

        result = augment_report(report, summarizer=mock_summarizer)
        assert result.is_ai_augmented is True
        assert "gw-tls-wildcard" in result.ai_summary
        assert "2 issues" in result.ai_summary

    def test_summarizer_gets_deep_copy(self):
        """Summarizer receives a copy — mutating it doesn't affect original."""
        report = _sample_report()
        original_count = len(report.findings)

        def mutating_summarizer(r: Report) -> str:
            # Attempt to mutate the passed report's findings list
            r.findings.clear()
            return "mutated"

        result = augment_report(report, summarizer=mutating_summarizer)
        # Original report should be untouched
        assert len(result.report.findings) == original_count


class TestCheckFaithfulness:
    """Test the faithfulness validation function."""

    def test_faithful_summary_no_hallucinations(self):
        report = _sample_report()
        summary = "The gw-tls-wildcard finding is critical. Also check gw-annotation-enable-cors."
        hallucinated = check_faithfulness(report, summary)
        assert hallucinated == []

    def test_unfaithful_summary_detects_hallucination(self):
        report = _sample_report()
        summary = "Critical issue: dra-alpha-feature-gate requires attention."
        hallucinated = check_faithfulness(report, summary)
        assert "dra-alpha-feature-gate" in hallucinated

    def test_no_rule_ids_in_summary(self):
        report = _sample_report()
        summary = "Everything looks fine, no issues found."
        hallucinated = check_faithfulness(report, summary)
        assert hallucinated == []

    def test_mixed_faithful_and_hallucinated(self):
        report = _sample_report()
        summary = "Found gw-tls-wildcard (real) and helm-chart-api-v2 (hallucinated)."
        hallucinated = check_faithfulness(report, summary)
        assert "helm-chart-api-v2" in hallucinated
        assert "gw-tls-wildcard" not in hallucinated
