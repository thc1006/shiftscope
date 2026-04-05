"""Tests for JSON and Markdown renderers."""

from __future__ import annotations

import json

from shiftscope.core.models import Finding, Report, Severity
from shiftscope.render.json_renderer import render_json
from shiftscope.render.markdown_renderer import render_markdown


def _sample_report() -> Report:
    return Report(
        analyzer_name="gateway-api",
        analyzer_version="0.1.0",
        source="examples/ingress-nginx/basic.yaml",
        findings=[
            Finding(
                rule_id="gw-cors-annotation",
                severity=Severity.WARNING,
                title="CORS annotation detected",
                detail="enable-cors annotation has partial Gateway API coverage.",
                evidence="nginx.ingress.kubernetes.io/enable-cors: 'true'",
                recommendation="Use HTTPRoute CORS filter.",
            ),
            Finding(
                rule_id="gw-tls-wildcard",
                severity=Severity.CRITICAL,
                title="Wildcard TLS host",
                detail="Wildcard TLS hosts require ListenerSet review.",
                evidence="spec.tls.hosts: ['*.example.com']",
                recommendation="Review certificate overlap and listener strategy.",
            ),
        ],
        metadata={"target_profile": "envoy-gateway"},
    )


class TestJsonRenderer:
    def test_render_json_is_valid_json(self):
        report = _sample_report()
        output = render_json(report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_render_json_contains_analyzer_info(self):
        report = _sample_report()
        parsed = json.loads(render_json(report))
        assert parsed["analyzer_name"] == "gateway-api"
        assert parsed["analyzer_version"] == "0.1.0"

    def test_render_json_contains_findings(self):
        report = _sample_report()
        parsed = json.loads(render_json(report))
        assert len(parsed["findings"]) == 2
        assert parsed["findings"][0]["rule_id"] == "gw-cors-annotation"

    def test_render_json_contains_metadata(self):
        report = _sample_report()
        parsed = json.loads(render_json(report))
        assert parsed["metadata"]["target_profile"] == "envoy-gateway"

    def test_render_json_empty_findings(self):
        report = Report(analyzer_name="a", analyzer_version="0.1.0", source="s", findings=[])
        parsed = json.loads(render_json(report))
        assert parsed["findings"] == []

    def test_render_json_is_indented(self):
        report = _sample_report()
        output = render_json(report)
        assert "\n" in output  # indented, not single-line


class TestMarkdownRenderer:
    def test_render_markdown_contains_title(self):
        report = _sample_report()
        md = render_markdown(report)
        assert "# Migration Report" in md or "# ShiftScope" in md or "gateway-api" in md

    def test_render_markdown_contains_findings(self):
        report = _sample_report()
        md = render_markdown(report)
        assert "gw-cors-annotation" in md
        assert "gw-tls-wildcard" in md

    def test_render_markdown_contains_severity(self):
        report = _sample_report()
        md = render_markdown(report)
        assert "warning" in md.lower() or "WARNING" in md
        assert "critical" in md.lower() or "CRITICAL" in md

    def test_render_markdown_contains_recommendations(self):
        report = _sample_report()
        md = render_markdown(report)
        assert "HTTPRoute CORS filter" in md
        assert "certificate overlap" in md

    def test_render_markdown_empty_findings(self):
        report = Report(analyzer_name="a", analyzer_version="0.1.0", source="s", findings=[])
        md = render_markdown(report)
        assert "No findings" in md or "0 finding" in md
