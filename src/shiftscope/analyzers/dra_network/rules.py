"""DRA networking migration rules."""

from __future__ import annotations

from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule


class AlphaFeatureGateRule(Rule):
    """Detects alpha DRA feature flags that should not be used on production."""

    rule_id = "dra-alpha-feature-gate"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("alpha"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        alpha = context.get("alpha", {})
        enabled = [k for k, v in alpha.items() if v]
        if not enabled:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Alpha DRA feature(s) enabled: {', '.join(enabled)}",
            detail="These DRA networking extensions are alpha and not suitable for production without explicit feature-gate planning.",
            evidence=f"alpha flags: {', '.join(f'{k}=true' for k in enabled)}",
            recommendation="Disable alpha flags for production; use only on test clusters with DynamicResourceAllocation feature gate.",
        )


class RDMABandwidthRule(Rule):
    """Detects high-bandwidth RDMA requirements that need DRA device class configuration."""

    rule_id = "dra-rdma-bandwidth"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("requires_rdma", False) or context.get("min_bandwidth_gbps") is not None

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if not context.get("requires_rdma") and context.get("min_bandwidth_gbps") is None:
            return None
        parts = []
        if context.get("requires_rdma"):
            parts.append("RDMA required")
        bw = context.get("min_bandwidth_gbps")
        if bw is not None:
            parts.append(f"min bandwidth {bw} Gbps")
        gpu = context.get("gpu_count", 0)
        if gpu > 0:
            parts.append(f"{gpu} GPUs")
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"High-performance networking: {', '.join(parts)}",
            detail="This intent requires RDMA or high-bandwidth networking. DRA DeviceClass must include CEL selectors for RDMA capability and bandwidth constraints.",
            evidence=f"requires_rdma={context.get('requires_rdma')}, min_bandwidth_gbps={bw}, gpu_count={gpu}",
            recommendation="Configure DeviceClass with CEL selectors for RDMA attributes and ResourceClaimTemplate with bandwidth constraints.",
        )


class LegacyBridgeRule(Rule):
    """Detects legacy bridge mode for SR-IOV/Multus migration path."""

    rule_id = "dra-legacy-bridge"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("legacy_bridge", False)

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if not context.get("legacy_bridge"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Legacy bridge mode enabled",
            detail="Legacy bridge generates SR-IOV/Multus compatible output alongside DRA manifests. This is a migration path, not the target end-state.",
            evidence=f"legacy_bridge=true, requires_rdma={context.get('requires_rdma')}, gpu_count={context.get('gpu_count', 0)}",
            recommendation="Plan migration from legacy extended resources to DRA ResourceClaims.",
        )


class TopologyAlignmentRule(Rule):
    """Detects topology alignment requirements for NUMA/PCI-aware scheduling."""

    rule_id = "dra-topology-alignment"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("require_topology_alignment", False)

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if not context.get("require_topology_alignment"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Topology alignment required",
            detail="NUMA/PCI topology alignment is required. DRA ResourceClaimTemplate must include topology constraints.",
            evidence=f"require_topology_alignment=true, gpu_count={context.get('gpu_count', 0)}",
            recommendation="Add topology-alignment constraint to ResourceClaimTemplate and verify Topology Manager configuration.",
        )


class InvalidWorkloadKindRule(Rule):
    """Validates workload_kind is a supported type."""

    rule_id = "dra-invalid-workload-kind"
    severity = Severity.CRITICAL

    _VALID_KINDS = {"Job", "Pod", "RayJob"}

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "workload_kind" in context

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        kind = context.get("workload_kind", "Job")
        if kind in self._VALID_KINDS:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Invalid workload_kind: '{kind}'",
            detail=f"workload_kind must be one of {sorted(self._VALID_KINDS)}. DRA manifests cannot be generated for unsupported kinds.",
            evidence=f"workload_kind={kind!r}",
            recommendation=f"Change workload_kind to one of: {', '.join(sorted(self._VALID_KINDS))}.",
        )


def build_rules() -> list[Rule]:
    """Build the complete rule set for DRA networking migration analysis."""
    return [
        AlphaFeatureGateRule(),
        RDMABandwidthRule(),
        LegacyBridgeRule(),
        TopologyAlignmentRule(),
        InvalidWorkloadKindRule(),
    ]
