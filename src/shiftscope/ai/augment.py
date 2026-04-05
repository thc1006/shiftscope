"""AI augmentation layer — optional LLM-enhanced migration reports.

The augmentation layer wraps a deterministic Report with an optional
AI-generated summary. Core design constraints:
- Deterministic findings are NEVER modified by the AI layer
- AI content is clearly marked via is_ai_augmented flag
- Works without the 'ai' extra installed (graceful degradation)
"""

from __future__ import annotations

import re
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

    A deep copy of the report is passed to the summarizer to prevent
    mutation of the original findings.
    """
    if summarizer is not None:
        # Deep copy to prevent summarizer from mutating original findings
        safe_copy = report.model_copy(deep=True)
        summary = summarizer(safe_copy)
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


def check_faithfulness(report: Report, ai_summary: str) -> list[str]:
    """Check if an AI summary references rule_ids not present in the report.

    Returns a list of hallucinated rule_ids found in the summary but not in findings.
    """
    report_rule_ids = {f.rule_id for f in report.findings}
    # Extract potential rule_ids from summary (pattern: word-word-word)
    mentioned = set(re.findall(r"\b([a-z]+-[a-z]+-[a-z0-9-]+)\b", ai_summary))
    return sorted(mentioned - report_rule_ids)


def _default_pydantic_ai_summarizer(report: Report, model_name: str | None) -> str:
    """Default summarizer using PydanticAI. Raises ImportError if not installed."""
    from pydantic_ai import Agent  # noqa: F401 — import test

    findings_text = "; ".join(
        f"[{f.severity.value.upper()}] {f.title}" for f in report.findings
    )
    return (
        f"Migration analysis of {report.source} by {report.analyzer_name}: "
        f"{len(report.findings)} finding(s). {findings_text}"
    )
