"""Table renderer for ShiftScope reports.

Compact terminal output showing rule_id, severity, and title columns via Rich.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from shiftscope.core.models import Report

SEVERITY_STYLES = {"critical": "bold red", "warning": "yellow", "info": "green"}


def render_table(report: Report) -> str:
    """Render a Report as a compact Rich table (rule_id, severity, title)."""
    tbl = Table(title=f"{report.analyzer_name} v{report.analyzer_version} \u2014 {report.source}")
    tbl.add_column("Rule ID", style="cyan", no_wrap=True)
    tbl.add_column("Severity", no_wrap=True)
    tbl.add_column("Title")

    for f in report.findings:
        style = SEVERITY_STYLES.get(f.severity.value, "")
        tbl.add_row(f.rule_id, f"[{style}]{f.severity.value}[/{style}]", f.title)

    console = Console(record=True)
    console.print(tbl)
    return console.export_text()
