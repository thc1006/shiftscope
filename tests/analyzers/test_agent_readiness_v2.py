"""Tests for Agent Readiness v2 — cost governance, OTel, FinOps rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shiftscope.core.models import Report, Severity

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture
def analyzer():
    from shiftscope.analyzers.agent_readiness.analyzer import AgentReadinessAnalyzer

    return AgentReadinessAnalyzer()


class TestCostNoBudget:
    def test_no_budget_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-no-budget")
        ctx = {"agent_name": "test", "token_budget_limit": 0}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_budget_set_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-no-budget")
        ctx = {"agent_name": "test", "token_budget_limit": 50000}
        assert rule.evaluate(ctx) is None


class TestCostNoLoopGuard:
    def test_no_loop_guard_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-no-loop-guard")
        ctx = {"agent_name": "test", "max_iterations": None}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_loop_guard_set_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-no-loop-guard")
        ctx = {"agent_name": "test", "max_iterations": 100}
        assert rule.evaluate(ctx) is None


class TestCostUnboundedRetry:
    def test_no_retry_policy_flagged(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-unbounded-retry")
        ctx = {"agent_name": "test", "retry_policy": None}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING

    def test_retry_policy_set_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "agent-cost-unbounded-retry")
        ctx = {"agent_name": "test", "retry_policy": {"max_retries": 3, "backoff": "exponential"}}
        assert rule.evaluate(ctx) is None


class TestNoKillSwitch:
    def test_no_kill_switch_flagged(self, analyzer):
        rule = next(
            r for r in analyzer.list_rules() if r.rule_id == "agent-governance-no-kill-switch"
        )
        ctx = {"agent_name": "test", "kill_switch": False}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_kill_switch_enabled_no_finding(self, analyzer):
        rule = next(
            r for r in analyzer.list_rules() if r.rule_id == "agent-governance-no-kill-switch"
        )
        ctx = {"agent_name": "test", "kill_switch": True}
        assert rule.evaluate(ctx) is None


class TestNoAuditTrail:
    def test_no_audit_flagged(self, analyzer):
        rule = next(
            r for r in analyzer.list_rules() if r.rule_id == "agent-governance-no-audit-trail"
        )
        ctx = {"agent_name": "test", "cost_evidence_logging": False}
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_audit_enabled_no_finding(self, analyzer):
        rule = next(
            r for r in analyzer.list_rules() if r.rule_id == "agent-governance-no-audit-trail"
        )
        ctx = {"agent_name": "test", "cost_evidence_logging": True}
        assert rule.evaluate(ctx) is None


class TestNoGraduatedResponse:
    def test_no_graduated_response_flagged(self, analyzer):
        rule = next(
            r
            for r in analyzer.list_rules()
            if r.rule_id == "agent-governance-no-graduated-response"
        )
        ctx = {"agent_name": "test", "graduated_response": None}
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_graduated_response_set_no_finding(self, analyzer):
        rule = next(
            r
            for r in analyzer.list_rules()
            if r.rule_id == "agent-governance-no-graduated-response"
        )
        ctx = {
            "agent_name": "test",
            "graduated_response": {"75": "alert", "90": "downgrade", "100": "stop"},
        }
        assert rule.evaluate(ctx) is None


class TestAgentReadinessV2Integration:
    def test_ungoverned_agent_many_findings(self, analyzer):
        report = analyzer.analyze(str(EXAMPLES / "agent-config-ungoverned.json"))
        assert isinstance(report, Report)
        # Ungoverned agent should trigger multiple cost/governance findings
        critical = [f for f in report.findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 3  # no-budget + no-loop-guard + no-kill-switch + promotion-gate

    def test_well_governed_agent_fewer_findings(self, analyzer, tmp_path):
        config = tmp_path / "governed.json"
        config.write_text(
            json.dumps(
                {
                    "agent_name": "governed-bot",
                    "required_tools": ["sum"],
                    "allowed_tools": ["sum", "ask_user"],
                    "token_budget_limit": 50000,
                    "used_tokens": 10000,
                    "otel_enabled": True,
                    "trace_coverage_ratio": 0.95,
                    "max_iterations": 100,
                    "retry_policy": {"max_retries": 3},
                    "kill_switch": True,
                    "cost_evidence_logging": True,
                    "graduated_response": {"75": "alert", "90": "downgrade", "100": "stop"},
                }
            )
        )
        report = analyzer.analyze(str(config))
        critical = [f for f in report.findings if f.severity == Severity.CRITICAL]
        assert len(critical) == 0

    def test_list_rules_v2_count(self, analyzer):
        # v1 had 4 rules, v2 adds 6 more = 10 total
        assert len(analyzer.list_rules()) >= 10
