"""Agent readiness rules — security, observability, token budget, promotion gate."""

from __future__ import annotations

from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule

_WEIGHTS = {"security": 0.4, "observability": 0.35, "economics": 0.25}
_PROMOTE_THRESHOLD = 0.85
_HOLD_THRESHOLD = 0.65


class ToolAllowlistRule(Rule):
    """Blocks agents that require tools not in the approved allowlist."""

    rule_id = "agent-tool-allowlist"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "required_tools" in context and "allowed_tools" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        required = set(context.get("required_tools", []))
        allowed = set(context.get("allowed_tools", []))
        denied = sorted(required - allowed)
        if not denied:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"{len(denied)} tool(s) not in allowlist",
            detail="Agent requires tools that are not in the approved allowlist. Promotion blocked.",
            evidence=f"denied: {', '.join(denied)}",
            recommendation="Remove denied tools or update the allowlist after security review.",
        )


class TokenBudgetRule(Rule):
    """Flags agents exceeding their token budget."""

    rule_id = "agent-token-budget"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "used_tokens" in context and "token_budget_limit" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        used = context.get("used_tokens", 0)
        limit = context.get("token_budget_limit", 0)
        if limit <= 0 or used <= limit:
            return None
        overage = used - limit
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Token budget exceeded",
            detail=f"Agent used {used} tokens against a budget of {limit} ({overage} over).",
            evidence=f"used={used}, limit={limit}, overage={overage}",
            recommendation="Reduce token usage or increase budget after cost review.",
        )


class ObservabilityRule(Rule):
    """Flags agents without proper observability (OTEL + trace coverage)."""

    rule_id = "agent-observability"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "otel_enabled" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        otel = context.get("otel_enabled", False)
        coverage = context.get("trace_coverage_ratio", 0.0)
        if otel and coverage >= 0.8:
            return None
        issues = []
        if not otel:
            issues.append("OTEL not enabled")
        if coverage < 0.8:
            issues.append(f"trace coverage {coverage:.0%} < 80%")
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Observability gaps detected",
            detail="Production agents require OTEL tracing with >=80% trace coverage.",
            evidence=f"otel_enabled={otel}, trace_coverage={coverage:.0%}; issues: {', '.join(issues)}",
            recommendation="Enable OTEL and ensure trace coverage >= 80% before promotion.",
        )


class PromotionGateRule(Rule):
    """Combined promotion gate: security * 0.4 + observability * 0.35 + economics * 0.25."""

    rule_id = "agent-promotion-gate"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return all(
            k in context for k in ("security_score", "observability_score", "economics_score")
        )

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        sec = context.get("security_score", 0.0)
        obs = context.get("observability_score", 0.0)
        econ = context.get("economics_score", 0.0)
        total = (
            sec * _WEIGHTS["security"]
            + obs * _WEIGHTS["observability"]
            + econ * _WEIGHTS["economics"]
        )

        if total >= _PROMOTE_THRESHOLD:
            return None

        status = "hold" if total >= _HOLD_THRESHOLD else "block"
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Promotion gate: {status}",
            detail=f"Weighted score {total:.2f} < {_PROMOTE_THRESHOLD} threshold. "
            f"Security={sec:.2f}, Observability={obs:.2f}, Economics={econ:.2f}.",
            evidence=f"total={total:.2f}, status={status}",
            recommendation="Improve the lowest-scoring dimension before re-evaluating.",
        )


# --- v2 Cost Governance Rules (grounded in $47K LangChain incident) ---


class NoBudgetRule(Rule):
    """No token budget defined — primary cause of runaway agent costs."""

    rule_id = "agent-cost-no-budget"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "token_budget_limit" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        limit = context.get("token_budget_limit", 0)
        if limit and limit > 0:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No token budget defined",
            detail=(
                "Without a budget, agent costs are unbounded. "
                "The $47K LangChain incident ran 11 days with no cost limit."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, token_budget_limit={limit}",
            recommendation="Set max_cost_usd, max_tokens, or max_runtime_sec.",
        )


class NoLoopGuardRule(Rule):
    """No loop detection or max_iterations configured."""

    rule_id = "agent-cost-no-loop-guard"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "max_iterations" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("max_iterations"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No loop guard (max_iterations) configured",
            detail=(
                "Without loop detection, agents can enter infinite conversation loops. "
                "Two agents ping-ponged for 11 days in the $47K incident."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, max_iterations=None",
            recommendation="Set max_iterations and implement FuzzyLoopGuard for similar-but-not-identical patterns.",
        )


class UnboundedRetryRule(Rule):
    """No retry policy with backoff and kill-after-N."""

    rule_id = "agent-cost-unbounded-retry"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "retry_policy" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("retry_policy"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No retry policy configured",
            detail=(
                "Without exponential backoff and kill-after-N limits, "
                "silent retry cascades can triple hourly spend."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, retry_policy=None",
            recommendation="Configure exponential backoff with max retries (e.g., 3-5).",
        )


class NoKillSwitchRule(Rule):
    """No termination mechanism configured."""

    rule_id = "agent-governance-no-kill-switch"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "kill_switch" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("kill_switch"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No kill switch / termination mechanism",
            detail=(
                "Without an emergency stop, runaway agents cannot be terminated. "
                "OWASP ASI-10 (Rogue Agents) requires termination capability."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, kill_switch=false",
            recommendation="Implement kill switch with immediate effect on all active sessions.",
        )


class NoAuditTrailRule(Rule):
    """No cost evidence records emitted per action."""

    rule_id = "agent-governance-no-audit-trail"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "cost_evidence_logging" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("cost_evidence_logging"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No cost evidence logging",
            detail=(
                "Every expensive action should emit an immutable record with "
                "run_id, agent_id, action, estimated_cost_usd, policy_version."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, cost_evidence_logging=false",
            recommendation="Enable cost evidence logging with immutable audit records.",
        )


class NoGraduatedResponseRule(Rule):
    """No 75%/90%/100% budget threshold actions configured."""

    rule_id = "agent-governance-no-graduated-response"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "graduated_response" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("graduated_response"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="No graduated response thresholds",
            detail=(
                "Without graduated response (alert at 75%, downgrade at 90%, stop at 100%), "
                "budget overruns are only detected after the fact."
            ),
            evidence=f"agent={context.get('agent_name', '?')}, graduated_response=None",
            recommendation="Configure 75%→alert, 90%→downgrade model, 100%→circuit breaker.",
        )


def build_rules() -> list[Rule]:
    return [
        # v1 rules
        ToolAllowlistRule(),
        TokenBudgetRule(),
        ObservabilityRule(),
        PromotionGateRule(),
        # v2 cost governance rules
        NoBudgetRule(),
        NoLoopGuardRule(),
        UnboundedRetryRule(),
        NoKillSwitchRule(),
        NoAuditTrailRule(),
        NoGraduatedResponseRule(),
    ]
