"""Tests for Gateway API analyzer — TDD RED phase."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shiftscope.core.models import Finding, Report, Severity

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples" / "ingress-nginx"
BASIC_YAML = EXAMPLES_DIR / "basic.yaml"


@pytest.fixture
def analyzer():
    from analyzers.gateway_api.analyzer import GatewayApiAnalyzer
    return GatewayApiAnalyzer()


# --- Parser tests ---

class TestIngressParser:
    def test_parse_basic_ingress(self):
        from analyzers.gateway_api.parser import load_ingresses
        ingresses = load_ingresses(str(BASIC_YAML))
        assert len(ingresses) == 1
        assert ingresses[0]["name"] == "demo-web"
        assert ingresses[0]["namespace"] == "demo"

    def test_parse_annotations(self):
        from analyzers.gateway_api.parser import load_ingresses
        ingresses = load_ingresses(str(BASIC_YAML))
        annotations = ingresses[0]["annotations"]
        assert "nginx.ingress.kubernetes.io/enable-cors" in annotations
        assert "nginx.ingress.kubernetes.io/backend-protocol" in annotations
        assert "nginx.ingress.kubernetes.io/auth-tls-secret" in annotations

    def test_parse_tls_hosts(self):
        from analyzers.gateway_api.parser import load_ingresses
        ingresses = load_ingresses(str(BASIC_YAML))
        assert "*.example.com" in ingresses[0]["tls_hosts"]

    def test_parse_empty_file(self, tmp_path):
        from analyzers.gateway_api.parser import load_ingresses
        empty = tmp_path / "empty.yaml"
        empty.write_text("---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")
        assert load_ingresses(str(empty)) == []

    def test_parse_multi_document(self, tmp_path):
        from analyzers.gateway_api.parser import load_ingresses
        multi = tmp_path / "multi.yaml"
        multi.write_text(
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: a\nspec: {}\n"
            "---\n"
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: b\nspec: {}\n"
        )
        ingresses = load_ingresses(str(multi))
        assert len(ingresses) == 2


# --- Rule tests ---

class TestAnnotationRules:
    def test_known_annotation_produces_finding(self, analyzer):
        rules = analyzer.list_rules()
        cors_rule = next((r for r in rules if r.rule_id == "gw-annotation-enable-cors"), None)
        assert cors_rule is not None

        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/enable-cors": "true"},
            "tls_hosts": [],
        }
        finding = cors_rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "enable-cors" in finding.title

    def test_server_snippet_is_critical(self, analyzer):
        rules = analyzer.list_rules()
        snippet_rule = next((r for r in rules if r.rule_id == "gw-annotation-server-snippet"), None)
        assert snippet_rule is not None

        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/server-snippet": "proxy_set_header X-Real-IP $remote_addr;"},
            "tls_hosts": [],
        }
        finding = snippet_rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_unknown_annotation_produces_finding(self, analyzer):
        rules = analyzer.list_rules()
        unknown_rule = next((r for r in rules if r.rule_id == "gw-annotation-unknown"), None)
        assert unknown_rule is not None

        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/some-custom-thing": "val"},
            "tls_hosts": [],
        }
        finding = unknown_rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "unknown" in finding.title.lower() or "unmapped" in finding.title.lower()


class TestTLSRiskRules:
    def test_wildcard_tls_detected(self, analyzer):
        rules = analyzer.list_rules()
        wc_rule = next((r for r in rules if r.rule_id == "gw-tls-wildcard"), None)
        assert wc_rule is not None

        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {},
            "tls_hosts": ["*.example.com"],
        }
        finding = wc_rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_no_wildcard_no_finding(self, analyzer):
        rules = analyzer.list_rules()
        wc_rule = next(r for r in rules if r.rule_id == "gw-tls-wildcard")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {},
            "tls_hosts": ["app.example.com"],
        }
        assert wc_rule.evaluate(ctx) is None

    def test_frontend_mtls_detected(self, analyzer):
        rules = analyzer.list_rules()
        mtls_rule = next(r for r in rules if r.rule_id == "gw-tls-frontend-mtls")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/auth-tls-secret": "ns/ca"},
            "tls_hosts": [],
        }
        finding = mtls_rule.evaluate(ctx)
        assert finding is not None
        assert "mTLS" in finding.title or "coalescing" in finding.detail.lower()

    def test_backend_protocol_detected(self, analyzer):
        rules = analyzer.list_rules()
        bp_rule = next(r for r in rules if r.rule_id == "gw-tls-backend-protocol")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/backend-protocol": "HTTPS"},
            "tls_hosts": [],
        }
        finding = bp_rule.evaluate(ctx)
        assert finding is not None


# --- Analyzer integration tests ---

class TestGatewayApiAnalyzer:
    def test_analyze_basic_yaml(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        assert isinstance(report, Report)
        assert report.analyzer_name == "gateway-api"
        assert report.source == str(BASIC_YAML)
        assert len(report.findings) >= 3  # at least cors + backend-protocol + auth-tls + wildcard

    def test_analyze_finds_annotation_findings(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        rule_ids = [f.rule_id for f in report.findings]
        assert any("annotation" in rid for rid in rule_ids)

    def test_analyze_finds_tls_risks(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        rule_ids = [f.rule_id for f in report.findings]
        assert any("tls" in rid for rid in rule_ids)

    def test_analyze_with_target_profile(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML), target_profile="envoy-gateway")
        assert report.metadata.get("target_profile") == "envoy-gateway"

    def test_analyze_empty_file(self, analyzer, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
        report = analyzer.analyze(str(empty))
        assert report.findings == []

    def test_list_rules_returns_all(self, analyzer):
        rules = analyzer.list_rules()
        assert len(rules) >= 8  # 5 annotation + 3 TLS + 1 unknown

    def test_json_output_valid(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        json_str = report.model_dump_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["analyzer_name"] == "gateway-api"
        assert len(parsed["findings"]) >= 3
