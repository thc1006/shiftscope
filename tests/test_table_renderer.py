from __future__ import annotations

from shiftscope.core.models import Finding, Report, Severity
from shiftscope.render.table_renderer import render_table


def _make_report(findings=None):
    return Report(
        analyzer_name="test-analyzer",
        analyzer_version="1.0.0",
        source="test.yaml",
        findings=findings or [],
    )


class TestTableRenderer:
    def test_contains_findings(self):
        report = _make_report([
            Finding(
                rule_id="TST-001",
                severity=Severity.CRITICAL,
                title="something broke",
                detail="details",
                evidence="evidence",
                recommendation="fix it",
            ),
            Finding(
                rule_id="TST-002",
                severity=Severity.INFO,
                title="just info",
                detail="details",
                evidence="evidence",
                recommendation="none",
            ),
        ])
        out = render_table(report)
        assert "TST-001" in out
        assert "TST-002" in out
        assert "critical" in out
        assert "info" in out
        assert "something broke" in out

    def test_empty_findings(self):
        report = _make_report()
        out = render_table(report)
        assert "test-analyzer" in out
