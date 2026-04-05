"""JSON renderer for ShiftScope reports."""

from __future__ import annotations

from shiftscope.core.models import Report


def render_json(report: Report, indent: int = 2) -> str:
    """Render a Report as indented JSON string."""
    return report.model_dump_json(indent=indent)
