"""Helm 4 / Charts v3 readiness rules."""

from __future__ import annotations

import re
from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule


class ChartApiV2Rule(Rule):
    """Detects Chart API v2 — still supported but v3 features require migration."""

    rule_id = "helm-chart-api-v2"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("api_version") == "v2"

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("api_version") != "v2":
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Chart still on API v2",
            detail="Helm 4 continues to support v2, but new capabilities (sequencing, alternate render engines, signer plugins) land on the v3 roadmap.",
            evidence=f"Chart.yaml apiVersion: v2",
            recommendation="Create v3 migration backlog; do not force-convert immediately.",
        )


class GoTemplateHeavyRule(Rule):
    """Detects heavy Go template composition that complicates render engine migration."""

    rule_id = "helm-go-template-heavy"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("templates_content"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        content = context.get("templates_content", "")
        if "{{- include" not in content and "{{ include" not in content:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Heavy Go template composition detected",
            detail="Alternate render engines (CUE, YAMLScript) are a Charts v3 motivation. Heavy template coupling makes future engine migration harder.",
            evidence="templates contain include/template markers",
            recommendation="Separate data shaping from rendering logic.",
        )


class OrderingNeedsReviewRule(Rule):
    """Detects suspected resource sequencing needs."""

    rule_id = "helm-ordering-needs-review"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("templates_content"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        content = context.get("templates_content", "")
        if "dependsOn" not in content and "hook-weight" not in content:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Resource sequencing needs detected",
            detail="Resource sequencing is a core Charts v3 requirement (HIP-0025).",
            evidence="templates contain ordering-related hints (dependsOn/hook-weight)",
            recommendation="Map to ordered-batch design for Charts v3 readiness.",
        )


class HelmignoreParityRule(Rule):
    """Detects .helmignore patterns that may be limited by current semantics."""

    rule_id = "helm-helmignore-parity"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("helmignore"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        hi = context.get("helmignore", "")
        if "**" not in hi and "/" not in hi:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=".helmignore may have limited semantics",
            detail=".helmignore ↔ .gitignore parity is a long-standing request addressed in Charts v3.",
            evidence=".helmignore contains wildcard/path-sensitive patterns",
            recommendation="Include ignore semantics review in migration plan.",
        )


class ValuesTransformRule(Rule):
    """Detects values.yaml structures that may need parent/subchart transform."""

    rule_id = "helm-values-transform"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("values_text"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        text = context.get("values_text", "")
        if not re.search(r"(?m)^[A-Za-z0-9_-]+:\s*$", text):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Values may need parent/subchart transform",
            detail="Parent/subchart values transform is a Charts v3 plugin candidate.",
            evidence="values.yaml contains nested top-level maps",
            recommendation="Add to values-transform plugin readiness backlog.",
        )


def build_rules() -> list[Rule]:
    """Build the complete rule set for Helm 4 readiness analysis."""
    return [
        ChartApiV2Rule(),
        GoTemplateHeavyRule(),
        OrderingNeedsReviewRule(),
        HelmignoreParityRule(),
        ValuesTransformRule(),
    ]
