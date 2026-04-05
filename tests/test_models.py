"""Tests for core data models ."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from shiftscope.core.models import Finding, Report, Severity


class TestSeverity:
    def test_severity_values(self):
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.CRITICAL == "critical"

    def test_severity_is_string_enum(self):
        assert isinstance(Severity.INFO, str)
        assert Severity("info") == Severity.INFO

    def test_severity_invalid_raises(self):
        with pytest.raises(ValueError):
            Severity("invalid")


class TestFinding:
    def test_create_finding(self):
        f = Finding(
            rule_id="gw-tls-coalescing-risk",
            severity=Severity.CRITICAL,
            title="HTTP/2 connection coalescing risk",
            detail="TLSRoute may cause coalescing issues with shared certificates.",
            evidence="spec.tls.hosts: ['*.example.com']",
            recommendation="Review TLSRoute usage and certificate overlap.",
        )
        assert f.rule_id == "gw-tls-coalescing-risk"
        assert f.severity == Severity.CRITICAL
        assert f.title == "HTTP/2 connection coalescing risk"

    def test_finding_severity_validation(self):
        with pytest.raises(ValidationError):
            Finding(
                rule_id="test",
                severity="invalid_severity",
                title="t",
                detail="d",
                evidence="e",
                recommendation="r",
            )

    def test_finding_required_fields(self):
        with pytest.raises(ValidationError):
            Finding(rule_id="test", severity=Severity.INFO)

    def test_finding_json_roundtrip(self):
        f = Finding(
            rule_id="test-rule",
            severity=Severity.WARNING,
            title="Test",
            detail="Detail",
            evidence="Evidence",
            recommendation="Fix it",
        )
        json_str = f.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["rule_id"] == "test-rule"
        assert parsed["severity"] == "warning"

        restored = Finding.model_validate_json(json_str)
        assert restored == f

    def test_finding_json_schema_generation(self):
        schema = Finding.model_json_schema()
        assert "properties" in schema
        assert "rule_id" in schema["properties"]
        assert "severity" in schema["properties"]


class TestReport:
    def test_create_empty_report(self):
        r = Report(
            analyzer_name="gateway-api",
            analyzer_version="0.1.0",
            source="test.yaml",
            findings=[],
        )
        assert r.analyzer_name == "gateway-api"
        assert r.findings == []
        assert r.metadata == {}

    def test_report_with_findings(self):
        f = Finding(
            rule_id="test",
            severity=Severity.INFO,
            title="Test finding",
            detail="d",
            evidence="e",
            recommendation="r",
        )
        r = Report(
            analyzer_name="test-analyzer",
            analyzer_version="1.0.0",
            source="input.yaml",
            findings=[f],
            metadata={"profile": "envoy-gateway"},
        )
        assert len(r.findings) == 1
        assert r.findings[0].rule_id == "test"
        assert r.metadata["profile"] == "envoy-gateway"

    def test_report_json_roundtrip(self):
        f = Finding(
            rule_id="r1",
            severity=Severity.WARNING,
            title="T",
            detail="D",
            evidence="E",
            recommendation="R",
        )
        r = Report(
            analyzer_name="a",
            analyzer_version="0.1.0",
            source="s",
            findings=[f],
        )
        json_str = r.model_dump_json(indent=2)
        restored = Report.model_validate_json(json_str)
        assert restored == r
        assert len(restored.findings) == 1

    def test_report_json_schema_generation(self):
        schema = Report.model_json_schema()
        assert "properties" in schema
        assert "findings" in schema["properties"]
        assert "analyzer_name" in schema["properties"]

    def test_report_metadata_defaults_to_empty(self):
        r = Report(
            analyzer_name="a",
            analyzer_version="0.1.0",
            source="s",
            findings=[],
        )
        assert r.metadata == {}

    def test_report_findings_count(self):
        findings = [
            Finding(
                rule_id=f"rule-{i}",
                severity=Severity.INFO,
                title=f"Finding {i}",
                detail="d",
                evidence="e",
                recommendation="r",
            )
            for i in range(5)
        ]
        r = Report(
            analyzer_name="a",
            analyzer_version="0.1.0",
            source="s",
            findings=findings,
        )
        assert len(r.findings) == 5
