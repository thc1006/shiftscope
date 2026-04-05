"""Gateway API migration analyzer — Ingress NGINX → Gateway API.

v2: Behavioral detection + annotation mapping + TLS risk analysis.
Supports cross-Ingress analysis (grouping by hostname for behavioral rules).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from shiftscope.analyzers.gateway_api.behavioral_rules import build_behavioral_rules
from shiftscope.analyzers.gateway_api.parser import load_ingresses
from shiftscope.analyzers.gateway_api.rules import build_rules
from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule

_CROSS_INGRESS_RULE_IDS = frozenset(
    {
        "gw-behavior-regex-global",
        "gw-behavior-rewrite-implies-regex",
        "gw-behavior-host-merge",
    }
)


class GatewayApiAnalyzer(Analyzer):
    """Analyzes Ingress NGINX manifests for Gateway API migration readiness.

    Detects:
    - Annotation portability issues (v1 rules)
    - TLS/mTLS risks (v1 rules)
    - Behavioral differences that silently break traffic (v2 behavioral rules)
    - Cross-Ingress interactions (regex-global, rewrite-implies-regex, host-merge)
    """

    name = "gateway-api"
    version = "0.2.0"
    description = "Ingress NGINX → Gateway API migration intelligence"

    def __init__(self) -> None:
        self._annotation_rules = build_rules()
        self._behavioral_rules = build_behavioral_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        """Analyze an Ingress manifest file for Gateway API migration."""
        ingresses = load_ingresses(input_path)
        all_findings = []

        # Phase 1: Per-Ingress annotation + TLS rules
        for ingress in ingresses:
            context = {
                "ingress_name": ingress["name"],
                "ingress_namespace": ingress["namespace"],
                "annotations": ingress["annotations"],
                "tls_hosts": ingress["tls_hosts"],
                "rules": ingress["rules"],
                "paths": _extract_paths(ingress),
            }
            all_findings.extend(self._run_rule_set(self._annotation_rules, context))

        # Phase 2: Per-Ingress behavioral rules
        per_ingress_rules = [
            r for r in self._behavioral_rules if r.rule_id not in _CROSS_INGRESS_RULE_IDS
        ]
        for idx, ingress in enumerate(ingresses):
            context = {
                "ingress_name": ingress["name"],
                "ingress_namespace": ingress["namespace"],
                "annotations": ingress["annotations"],
                "paths": _extract_paths(ingress),
                "_is_first_ingress": idx == 0,
                "_total_ingress_count": len(ingresses),
            }
            all_findings.extend(self._run_rule_set(per_ingress_rules, context))

        # Phase 3: Cross-Ingress behavioral rules (grouped by hostname)
        cross_rules = [r for r in self._behavioral_rules if r.rule_id in _CROSS_INGRESS_RULE_IDS]
        host_groups = _group_by_hostname(ingresses)
        for hostname, group in host_groups.items():
            context = {"hostname": hostname, "host_group": group}
            all_findings.extend(self._run_rule_set(cross_rules, context))

        metadata: dict[str, Any] = {"ingress_count": len(ingresses)}
        if "target_profile" in kwargs:
            metadata["target_profile"] = kwargs["target_profile"]

        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=all_findings,
            metadata=metadata,
        )

    def list_rules(self) -> list[Rule]:
        return list(self._annotation_rules) + list(self._behavioral_rules)

    @staticmethod
    def _run_rule_set(rules: list[Rule], context: dict[str, Any]) -> list:
        """Run a specific set of rules with the same resilience as Analyzer.run_rules."""
        import logging

        from shiftscope.core.models import Finding, Severity

        logger = logging.getLogger(__name__)
        findings = []
        for rule in rules:
            try:
                if rule.applies_to(context):
                    finding = rule.evaluate(context)
                    if finding is not None:
                        findings.append(finding)
            except Exception as exc:
                error_summary = f"{type(exc).__name__}: {exc}"
                logger.warning("Rule '%s' raised: %s", rule.rule_id, error_summary)
                logger.debug("Rule '%s' traceback", rule.rule_id, exc_info=True)
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=Severity.CRITICAL,
                        title=f"Rule '{rule.rule_id}' failed",
                        detail=f"Unexpected exception: {error_summary}",
                        evidence=f"rule_id={rule.rule_id}",
                        recommendation="Report to analyzer maintainer.",
                    )
                )
        return findings


def _extract_paths(ingress: dict[str, Any]) -> list[dict[str, str]]:
    """Extract path entries from Ingress rules."""
    paths = []
    for rule in ingress.get("rules", []):
        for p in (rule.get("http") or {}).get("paths", []):
            paths.append(
                {
                    "path": p.get("path", ""),
                    "pathType": p.get("pathType", ""),
                }
            )
    return paths


def _group_by_hostname(ingresses: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group Ingresses by their hostname(s) for cross-Ingress analysis.

    Each Ingress appears at most once per hostname group (deduplicated).
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for ingress in ingresses:
        for rule in ingress.get("rules", []):
            host = rule.get("host", "")
            if host and ingress["name"] not in seen[host]:
                groups[host].append(ingress)
                seen[host].add(ingress["name"])
    return dict(groups)
