"""Tests for agent readiness analyzer."""

from __future__ import annotations

import json

import pytest

from shiftscope.core.models import Report, Severity


@pytest.fixture
def analyzer():
    from shiftscope.analyzers.agent_readiness.analyzer import AgentReadinessAnalyzer

    return AgentReadinessAnalyzer()


class TestAgentReadinessRules:
    def test_tool_allowlist_violation(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-tool-allowlist")
        ctx = {
            "agent_name": "test",
            "required_tools": ["sum", "print_environment"],
            "allowed_tools": ["sum", "ask_user"],
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL
        assert "print_environment" in finding.evidence

    def test_tool_allowlist_pass(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-tool-allowlist")
        ctx = {
            "agent_name": "test",
            "required_tools": ["sum"],
            "allowed_tools": ["sum", "ask_user"],
        }
        assert rule.evaluate(ctx) is None

    def test_token_budget_overrun(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-token-budget")
        ctx = {"agent_name": "test", "used_tokens": 60000, "token_budget_limit": 50000}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING

    def test_token_budget_ok(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-token-budget")
        ctx = {"agent_name": "test", "used_tokens": 10000, "token_budget_limit": 50000}
        assert rule.evaluate(ctx) is None

    def test_missing_otel(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-observability")
        ctx = {"agent_name": "test", "otel_enabled": False, "trace_coverage_ratio": 0.0}
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_otel_ok(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-observability")
        ctx = {"agent_name": "test", "otel_enabled": True, "trace_coverage_ratio": 0.95}
        assert rule.evaluate(ctx) is None

    def test_promotion_blocked(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-promotion-gate")
        ctx = {
            "agent_name": "test",
            "security_score": 0.3,
            "observability_score": 0.2,
            "economics_score": 0.1,
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL
        assert "block" in finding.evidence.lower()

    def test_promotion_ready(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-promotion-gate")
        ctx = {
            "agent_name": "test",
            "security_score": 0.95,
            "observability_score": 0.90,
            "economics_score": 0.85,
        }
        assert rule.evaluate(ctx) is None


class TestAgentReadinessAnalyzer:
    def test_analyze_safe_agent(self, analyzer, tmp_path):
        config = tmp_path / "safe.json"
        config.write_text(
            json.dumps(
                {
                    "agent_name": "safe-agent",
                    "required_tools": ["sum"],
                    "allowed_tools": ["sum", "ask_user"],
                    "token_budget_limit": 50000,
                    "used_tokens": 10000,
                    "otel_enabled": True,
                    "trace_coverage_ratio": 0.95,
                }
            )
        )
        report = analyzer.analyze(str(config))
        assert isinstance(report, Report)
        assert report.analyzer_name == "agent-readiness"
        # Safe agent should have no critical findings
        critical = [f for f in report.findings if f.severity == Severity.CRITICAL]
        assert len(critical) == 0

    def test_analyze_unsafe_agent(self, analyzer, tmp_path):
        config = tmp_path / "unsafe.json"
        config.write_text(
            json.dumps(
                {
                    "agent_name": "unsafe-agent",
                    "required_tools": ["sum", "print_environment", "exec_shell"],
                    "allowed_tools": ["sum"],
                    "token_budget_limit": 50000,
                    "used_tokens": 80000,
                    "otel_enabled": False,
                    "trace_coverage_ratio": 0.0,
                }
            )
        )
        report = analyzer.analyze(str(config))
        assert len(report.findings) >= 2

    def test_list_rules_count(self, analyzer):
        assert len(analyzer.list_rules()) >= 4

    def test_json_roundtrip(self, analyzer, tmp_path):
        config = tmp_path / "test.json"
        config.write_text(
            json.dumps(
                {
                    "agent_name": "test",
                    "required_tools": ["sum"],
                    "allowed_tools": ["sum"],
                    "token_budget_limit": 50000,
                    "used_tokens": 10000,
                    "otel_enabled": True,
                    "trace_coverage_ratio": 0.9,
                }
            )
        )
        report = analyzer.analyze(str(config))
        restored = Report.model_validate_json(report.model_dump_json())
        assert len(restored.findings) == len(report.findings)
