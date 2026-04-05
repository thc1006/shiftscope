"""Tests for Gateway API analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from shiftscope.analyzers.gateway_api.analyzer import GatewayApiAnalyzer
from shiftscope.analyzers.gateway_api.parser import load_ingresses
from shiftscope.core.models import Report, Severity

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples" / "ingress-nginx"
BASIC_YAML = EXAMPLES_DIR / "basic.yaml"


@pytest.fixture
def analyzer():
    return GatewayApiAnalyzer()


# --- Parser tests ---


class TestIngressParser:
    def test_parse_basic_ingress(self):
        ingresses = load_ingresses(str(BASIC_YAML))
        assert len(ingresses) == 1
        assert ingresses[0]["name"] == "demo-web"
        assert ingresses[0]["namespace"] == "demo"

    def test_parse_annotations(self):
        ingresses = load_ingresses(str(BASIC_YAML))
        annotations = ingresses[0]["annotations"]
        assert "nginx.ingress.kubernetes.io/enable-cors" in annotations
        assert "nginx.ingress.kubernetes.io/backend-protocol" in annotations
        assert "nginx.ingress.kubernetes.io/auth-tls-secret" in annotations

    def test_parse_tls_hosts(self):
        ingresses = load_ingresses(str(BASIC_YAML))
        assert "*.example.com" in ingresses[0]["tls_hosts"]

    def test_parse_empty_file(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")
        assert load_ingresses(str(empty)) == []

    def test_parse_multi_document(self, tmp_path):
        multi = tmp_path / "multi.yaml"
        multi.write_text(
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: a\nspec: {}\n"
            "---\n"
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: b\nspec: {}\n"
        )
        ingresses = load_ingresses(str(multi))
        assert len(ingresses) == 2
        assert ingresses[0]["name"] == "a"
        assert ingresses[1]["name"] == "b"

    def test_parse_no_annotations(self, tmp_path):
        bare = tmp_path / "bare.yaml"
        bare.write_text(
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: bare\nspec: {}\n"
        )
        ingresses = load_ingresses(str(bare))
        assert ingresses[0]["annotations"] == {}
        assert ingresses[0]["tls_hosts"] == []


# --- Annotation rule tests ---


class TestAnnotationRules:
    def test_cors_annotation(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-enable-cors")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/enable-cors": "true"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "enable-cors" in finding.title

    def test_server_snippet_is_critical(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-server-snippet")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {
                "nginx.ingress.kubernetes.io/server-snippet": "proxy_set_header X-Real-IP $remote_addr;"
            },
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL
        assert "server-snippet" in finding.title

    def test_ssl_redirect_annotation(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-ssl-redirect")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/ssl-redirect": "true"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "HTTPRoute RequestRedirect" in finding.recommendation

    def test_backend_protocol_as_annotation(self, analyzer):
        rule = next(
            r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-backend-protocol"
        )
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/backend-protocol": "HTTPS"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_annotation_not_present_returns_none(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-enable-cors")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"unrelated": "val"},
            "tls_hosts": [],
        }
        assert rule.evaluate(ctx) is None

    def test_unknown_annotation(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-unknown")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/some-custom-thing": "val"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "unmapped" in finding.title.lower()

    def test_unknown_rule_ignores_non_nginx_annotations(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-annotation-unknown")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"app.kubernetes.io/name": "web"},
            "tls_hosts": [],
        }
        assert rule.evaluate(ctx) is None


# --- TLS risk rule tests ---


class TestTLSRiskRules:
    def test_wildcard_tls_detected(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-tls-wildcard")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {},
            "tls_hosts": ["*.example.com"],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL
        assert "wildcard" in finding.title.lower()

    def test_no_wildcard_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-tls-wildcard")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {},
            "tls_hosts": ["app.example.com"],
        }
        assert rule.evaluate(ctx) is None

    def test_frontend_mtls_detected(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-tls-frontend-mtls")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/auth-tls-secret": "ns/ca"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "mTLS" in finding.title

    def test_backend_protocol_tls_risk(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "gw-tls-backend-protocol")
        ctx = {
            "ingress_name": "test",
            "ingress_namespace": "default",
            "annotations": {"nginx.ingress.kubernetes.io/backend-protocol": "HTTPS"},
            "tls_hosts": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "BackendTLSPolicy" in finding.recommendation


# --- Analyzer integration tests ---


class TestGatewayApiAnalyzer:
    def test_analyze_basic_yaml(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        assert isinstance(report, Report)
        assert report.analyzer_name == "gateway-api"
        assert report.source == str(BASIC_YAML)
        # basic.yaml: 3 known annotations + wildcard TLS + frontend mTLS + backend protocol = 6
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-annotation-enable-cors" in rule_ids
        assert "gw-tls-wildcard" in rule_ids
        assert len(report.findings) >= 6

    def test_analyze_finding_rule_ids(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-annotation-enable-cors" in rule_ids
        assert "gw-annotation-backend-protocol" in rule_ids
        assert "gw-annotation-auth-tls-secret" in rule_ids
        assert "gw-tls-wildcard" in rule_ids
        assert "gw-tls-frontend-mtls" in rule_ids
        assert "gw-tls-backend-protocol" in rule_ids

    def test_analyze_with_target_profile(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML), target_profile="envoy-gateway")
        assert report.metadata["target_profile"] == "envoy-gateway"

    def test_analyze_metadata_has_ingress_count(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        assert report.metadata["ingress_count"] == 1

    def test_analyze_empty_file(self, analyzer, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
        report = analyzer.analyze(str(empty))
        assert report.findings == []
        assert report.metadata["ingress_count"] == 0

    def test_analyze_multi_ingress(self, analyzer, tmp_path):
        multi = tmp_path / "multi.yaml"
        multi.write_text(
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: a\n"
            "  annotations:\n    nginx.ingress.kubernetes.io/enable-cors: 'true'\nspec: {}\n"
            "---\n"
            "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: b\n"
            "  annotations:\n    nginx.ingress.kubernetes.io/server-snippet: 'x'\nspec: {}\n"
        )
        report = analyzer.analyze(str(multi))
        assert report.metadata["ingress_count"] == 2
        assert len(report.findings) >= 2
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-annotation-enable-cors" in rule_ids
        assert "gw-annotation-server-snippet" in rule_ids

    def test_list_rules_count(self, analyzer):
        rules = analyzer.list_rules()
        # 9 annotation + 9 behavioral = 18
        assert len(rules) == 18

    def test_json_roundtrip(self, analyzer):
        report = analyzer.analyze(str(BASIC_YAML))
        json_str = report.model_dump_json(indent=2)
        restored = Report.model_validate_json(json_str)
        assert restored.analyzer_name == "gateway-api"
        assert len(restored.findings) == len(report.findings)
