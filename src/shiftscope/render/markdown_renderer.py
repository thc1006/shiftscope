"""Markdown renderer for ShiftScope reports."""

from __future__ import annotations

from shiftscope.core.models import Report


def render_markdown(report: Report) -> str:
    """Render a Report as a Markdown document."""
    lines: list[str] = []
    lines.append(f"# Migration Report: {report.analyzer_name}")
    lines.append("")
    lines.append(f"- **Analyzer version:** {report.analyzer_version}")
    lines.append(f"- **Source:** `{report.source}`")
    lines.append(f"- **Findings:** {len(report.findings)}")

    if report.metadata:
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        for key, value in report.metadata.items():
            lines.append(f"- **{key}:** {value}")

    lines.append("")

    if not report.findings:
        lines.append("No findings detected.")
    else:
        lines.append("## Findings")
        lines.append("")

        for i, f in enumerate(report.findings, 1):
            severity_upper = str(f.severity).upper()
            lines.append(f"### {i}. [{severity_upper}] {f.title}")
            lines.append("")
            lines.append(f"- **Rule:** `{f.rule_id}`")
            lines.append(f"- **Detail:** {f.detail}")
            lines.append(f"- **Evidence:** `{f.evidence}`")
            lines.append(f"- **Recommendation:** {f.recommendation}")
            lines.append("")

    return "\n".join(lines)
