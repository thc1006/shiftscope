"""Telco intent provenance rules."""

from __future__ import annotations

from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule


class GitOpsTargetRule(Rule):
    """Flags Flux as GitOps target due to K8s version conflict with Nephio R6."""

    rule_id = "telco-gitops-target"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "gitops_target" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        target = context.get("gitops_target", "")
        if target != "flux":
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Flux selected as GitOps target",
            detail="Flux 2.8 K8s support starts at 1.33; Nephio R6 documented up to 1.32.0. Version mismatch risk.",
            evidence=f"gitops_target=flux, region={context.get('region', '?')}",
            recommendation="Use Argo CD as primary GitOps target; keep Flux as comparison only.",
        )


class ProvenanceReviewRule(Rule):
    """Flags configurations that require human review due to hydrated data."""

    rule_id = "telco-provenance-review"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("has_hydration", False) or context.get("require_ipv4", False)

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if not context.get("has_hydration") and not context.get("require_ipv4"):
            return None
        parts = []
        if context.get("has_hydration"):
            parts.append("hydrated data present")
        if context.get("require_ipv4"):
            parts.append("IPv4 allocation required")
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Provenance review required",
            detail="Fields derived from hydration or IPAM allocation require human review before production deployment.",
            evidence=", ".join(parts),
            recommendation="Review provenance ledger and confirm all hydrated values before promotion.",
        )


class SouthboundContractRule(Rule):
    """Notes that SDC southbound is contract-only, not a production CRD."""

    rule_id = "telco-southbound-contract"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("southbound_target") == "sdc"

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if context.get("southbound_target") != "sdc":
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="SDC southbound is contract-only",
            detail="SDC candidate payload is not an official CRD. Schema-aware validation adapter contract only.",
            evidence="southbound_target=sdc",
            recommendation="Do not treat rendered SDC payload as production-deployable without vendor validation.",
        )


def build_rules() -> list[Rule]:
    return [GitOpsTargetRule(), ProvenanceReviewRule(), SouthboundContractRule()]
