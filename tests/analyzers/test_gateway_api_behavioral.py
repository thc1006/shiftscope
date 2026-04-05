"""Tests for Gateway API v2 behavioral detection rules."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


@pytest.fixture
def analyzer():
    from shiftscope.analyzers.gateway_api.analyzer import GatewayApiAnalyzer

    return GatewayApiAnalyzer()


def _write_yaml(tmp_path: Path, content: str) -> str:
    f = tmp_path / "test.yaml"
    f.write_text(dedent(content))
    return str(f)


# --- Behavior 1: Regex prefix + case insensitive ---


class TestRegexPrefix:
    def test_use_regex_without_suffix_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
              annotations:
                nginx.ingress.kubernetes.io/use-regex: "true"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/[A-Z]{3}"
                    pathType: ImplementationSpecific
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-regex-prefix" in rule_ids


# --- Behavior 2: use-regex global per host ---


class TestRegexGlobal:
    def test_sibling_ingress_affected(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: regex-ingress
              annotations:
                nginx.ingress.kubernetes.io/use-regex: "true"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/api/.*"
                    pathType: ImplementationSpecific
                    backend:
                      service:
                        name: api-svc
                        port:
                          number: 80
            ---
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: normal-ingress
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/Header"
                    pathType: Exact
                    backend:
                      service:
                        name: web-svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-regex-global" in rule_ids


# --- Behavior 3: rewrite-target implies regex ---


class TestRewriteImpliesRegex:
    def test_rewrite_target_flags_siblings(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: rewrite-ingress
              annotations:
                nginx.ingress.kubernetes.io/rewrite-target: "/uuid"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/old"
                    pathType: Exact
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            ---
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: other-ingress
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/Header"
                    pathType: Exact
                    backend:
                      service:
                        name: svc2
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-rewrite-implies-regex" in rule_ids


# --- Behavior 4: trailing slash redirect ---


class TestTrailingSlash:
    def test_trailing_slash_flagged(self, analyzer, tmp_path):
        """Path WITHOUT trailing slash should fire — nginx auto-redirects, GW API won't."""
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/my-path"
                    pathType: Prefix
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-trailing-slash" in rule_ids

    def test_trailing_slash_present_no_flag(self, analyzer, tmp_path):
        """Path WITH trailing slash should NOT fire — already explicit."""
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: "/my-path/"
                    pathType: Exact
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-trailing-slash" not in rule_ids


# --- Behavior 7: snippet no equivalent ---


class TestSnippetNoEquiv:
    def test_configuration_snippet_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
              annotations:
                nginx.ingress.kubernetes.io/configuration-snippet: |
                  more_set_headers "X-Custom: value";
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-snippet-no-equiv" in rule_ids

    def test_server_snippet_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
              annotations:
                nginx.ingress.kubernetes.io/server-snippet: "listen 8080;"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-snippet-no-equiv" in rule_ids


# --- Behavior 8: canary ---


class TestCanary:
    def test_canary_annotation_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
              annotations:
                nginx.ingress.kubernetes.io/canary: "true"
                nginx.ingress.kubernetes.io/canary-weight: "20"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-canary" in rule_ids


# --- Behavior 9: affinity ---


class TestAffinity:
    def test_affinity_annotation_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: test
              annotations:
                nginx.ingress.kubernetes.io/affinity: "cookie"
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-affinity" in rule_ids


# --- Behavior 10: host merge ---


class TestHostMerge:
    def test_multiple_ingresses_same_host_flagged(self, analyzer, tmp_path):
        path = _write_yaml(
            tmp_path,
            """\
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: ingress-a
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /api
                    pathType: Prefix
                    backend:
                      service:
                        name: api-svc
                        port:
                          number: 80
            ---
            apiVersion: networking.k8s.io/v1
            kind: Ingress
            metadata:
              name: ingress-b
            spec:
              rules:
              - host: app.example.com
                http:
                  paths:
                  - path: /web
                    pathType: Prefix
                    backend:
                      service:
                        name: web-svc
                        port:
                          number: 80
            """,
        )
        report = analyzer.analyze(path)
        rule_ids = {f.rule_id for f in report.findings}
        assert "gw-behavior-host-merge" in rule_ids


# --- Integration: real-world examples ---


class TestRealWorldBehavioral:
    def test_basic_yaml_gets_behavioral_findings(self, analyzer):
        """The existing basic.yaml should now trigger behavioral rules too."""
        examples = Path(__file__).resolve().parents[2] / "examples" / "ingress-nginx"
        report = analyzer.analyze(str(examples / "basic.yaml"))
        rule_ids = {f.rule_id for f in report.findings}
        assert report.analyzer_name == "gateway-api"
        assert len(report.findings) >= 6
        # basic.yaml has one path with Exact type → should trigger path-normalization
        assert "gw-behavior-path-normalization" in rule_ids
