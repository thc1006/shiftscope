"""Agent readiness analyzer — evaluates AI agent production readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shiftscope.analyzers.agent_readiness.rules import build_rules
from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule


class AgentReadinessAnalyzer(Analyzer):
    """Evaluates AI agent configurations for production readiness."""

    name = "agent-readiness"
    version = "0.1.0"
    description = "AI agent pilot→production readiness assessment"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        context = dict(data)

        # Compute scores for promotion gate
        security = self._security_score(context)
        observability = self._observability_score(context)
        economics = self._economics_score(context)
        context["security_score"] = security
        context["observability_score"] = observability
        context["economics_score"] = economics

        findings = self.run_rules(context)
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata={"agent_name": data.get("agent_name", "")},
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)

    @staticmethod
    def _security_score(ctx: dict[str, Any]) -> float:
        required = set(ctx.get("required_tools", []))
        allowed = set(ctx.get("allowed_tools", []))
        if not allowed:
            return 0.0
        denied = required - allowed
        return 0.0 if denied else 1.0

    @staticmethod
    def _observability_score(ctx: dict[str, Any]) -> float:
        if not ctx.get("otel_enabled", False):
            return 0.0
        return float(ctx.get("trace_coverage_ratio", 0.0))

    @staticmethod
    def _economics_score(ctx: dict[str, Any]) -> float:
        limit = ctx.get("token_budget_limit", 0)
        used = ctx.get("used_tokens", 0)
        if limit <= 0:
            return 0.0
        return 1.0 if used <= limit else max(0.0, 1.0 - (used - limit) / limit)
