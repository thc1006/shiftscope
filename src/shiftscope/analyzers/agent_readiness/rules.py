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


def build_rules() -> list[Rule]:
    return [ToolAllowlistRule(), TokenBudgetRule(), ObservabilityRule(), PromotionGateRule()]
