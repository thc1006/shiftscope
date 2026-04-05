"""AI augmentation layer — optional LLM-enhanced migration reports.

The augmentation layer wraps a deterministic Report with an optional
AI-generated summary. Core design constraints:
- Deterministic findings are NEVER modified by the AI layer
- AI content is clearly marked via is_ai_augmented flag
- Works without the 'ai' extra installed (graceful degradation)
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, computed_field

from shiftscope.core.models import Report


class AugmentedReport(BaseModel):
    """A deterministic Report wrapped with optional AI-generated summary.

    The original report is immutable. The AI summary is supplementary
    and clearly separated from deterministic findings.
    """

    model_config = ConfigDict(frozen=True)

    report: Report
    ai_summary: str | None = None
    ai_model: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_ai_augmented(self) -> bool:
        """True if this report has an AI-generated summary."""
        return self.ai_summary is not None


def augment_report(
    report: Report,
    summarizer: Callable[[Report], str] | None = None,
    model_name: str | None = None,
) -> AugmentedReport:
    """Augment a deterministic Report with an optional AI summary.

    Args:
        report: The deterministic report to augment.
        summarizer: A callable that takes a Report and returns a summary string.
                    If None and PydanticAI is available, uses a default summarizer.
                    If None and PydanticAI is not available, returns report without AI.
        model_name: Name of the AI model used (for provenance tracking).

    Returns:
        AugmentedReport with the original report preserved and optional AI summary.
    """
    if summarizer is not None:
        summary = summarizer(report)
        return AugmentedReport(
            report=report,
            ai_summary=summary,
            ai_model=model_name or "custom",
        )

    # Try to use PydanticAI if available
    try:
        summary = _default_pydantic_ai_summarizer(report, model_name)
        return AugmentedReport(
            report=report,
            ai_summary=summary,
            ai_model=model_name or "pydantic-ai",
        )
    except ImportError:
        # PydanticAI not installed — return without AI augmentation
        return AugmentedReport(report=report)


def _default_pydantic_ai_summarizer(report: Report, model_name: str | None) -> str:
    """Default summarizer using PydanticAI. Raises ImportError if not installed."""
    from pydantic_ai import Agent  # noqa: F401 — import test

    # Placeholder: real PydanticAI integration would create an Agent
    # with a structured prompt here. For now, generate a deterministic
    # summary to validate the augmentation pipeline.
    findings_text = "; ".join(
        f"[{f.severity.value.upper()}] {f.title}" for f in report.findings
    )
    return (
        f"Migration analysis of {report.source} by {report.analyzer_name}: "
        f"{len(report.findings)} finding(s). {findings_text}"
    )
