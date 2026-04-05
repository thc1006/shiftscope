"""Tests for MCP Security analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from shiftscope.core.models import Report, Severity

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture
def analyzer():
    from shiftscope.analyzers.mcp_security.analyzer import MCPSecurityAnalyzer

    return MCPSecurityAnalyzer()


class TestMCPConfigParser:
    def test_parse_insecure_config(self):
        from shiftscope.analyzers.mcp_security.parser import parse_mcp_config

        config = parse_mcp_config(str(EXAMPLES / "mcp-config-insecure.json"))
        assert len(config["servers"]) == 3
        assert "filesystem" in config["servers"]

    def test_parse_secure_config(self):
        from shiftscope.analyzers.mcp_security.parser import parse_mcp_config

        config = parse_mcp_config(str(EXAMPLES / "mcp-config-secure.json"))
        assert len(config["servers"]) == 1
        assert config["servers"]["read-only-k8s"]["auth"]["type"] == "oauth2"


class TestStaticCredentials:
    def test_plaintext_api_key_detected(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-static-credentials")
        ctx = {
            "server_name": "test",
            "env": {"API_KEY": "sk-live-abc123def456"},
            "command": "npx",
            "args": [],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL
        assert "API_KEY" in finding.evidence

    def test_no_env_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-static-credentials")
        ctx = {"server_name": "test", "env": {}, "command": "npx", "args": []}
        assert rule.evaluate(ctx) is None


class TestMissingAuth:
    def test_no_auth_config_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-missing-auth")
        ctx = {"server_name": "test", "auth": None, "command": "npx", "args": []}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_oauth_configured_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-missing-auth")
        ctx = {
            "server_name": "test",
            "auth": {"type": "oauth2"},
            "command": "npx",
            "args": [],
        }
        assert rule.evaluate(ctx) is None


class TestOverPermission:
    def test_wildcard_commands_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-over-permission")
        ctx = {
            "server_name": "shell-runner",
            "env": {"ALLOWED_COMMANDS": "*"},
            "command": "python",
            "args": ["-m", "mcp_shell_server"],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_restricted_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-over-permission")
        ctx = {
            "server_name": "limited",
            "env": {"ALLOWED_COMMANDS": "ls,cat"},
            "command": "python",
            "args": [],
        }
        assert rule.evaluate(ctx) is None


class TestCommandInjection:
    def test_shell_server_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-command-injection")
        ctx = {
            "server_name": "shell",
            "command": "python",
            "args": ["-m", "mcp_shell_server"],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL


class TestSupplyChain:
    def test_unpinned_npx_package(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-supply-chain")
        ctx = {
            "server_name": "test",
            "command": "npx",
            "args": ["-y", "@some/mcp-server"],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "npx" in finding.evidence

    def test_pinned_version_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "mcp-sec-supply-chain")
        ctx = {
            "server_name": "test",
            "command": "npx",
            "args": ["@some/mcp-server@1.2.3"],
        }
        assert rule.evaluate(ctx) is None


class TestMCPSecurityAnalyzer:
    def test_insecure_config_multiple_findings(self, analyzer):
        report = analyzer.analyze(str(EXAMPLES / "mcp-config-insecure.json"))
        assert isinstance(report, Report)
        assert report.analyzer_name == "mcp-security"
        assert len(report.findings) >= 3
        severities = {f.severity for f in report.findings}
        assert Severity.CRITICAL in severities

    def test_secure_config_fewer_findings(self, analyzer):
        report = analyzer.analyze(str(EXAMPLES / "mcp-config-secure.json"))
        assert len(report.findings) < 3

    def test_list_rules(self, analyzer):
        assert len(analyzer.list_rules()) >= 5

    def test_json_roundtrip(self, analyzer):
        report = analyzer.analyze(str(EXAMPLES / "mcp-config-insecure.json"))
        restored = Report.model_validate_json(report.model_dump_json())
        assert len(restored.findings) == len(report.findings)

    def test_owasp_asi_in_findings(self, analyzer):
        """Each finding should reference OWASP ASI category in detail."""
        report = analyzer.analyze(str(EXAMPLES / "mcp-config-insecure.json"))
        asi_findings = [f for f in report.findings if "ASI-" in f.detail]
        assert len(asi_findings) >= 1
