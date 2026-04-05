"""Gateway API migration analyzer — Ingress NGINX → Gateway API.

Reference implementation of a ShiftScope analyzer plugin.
"""

from __future__ import annotations

from typing import Any

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule

from analyzers.gateway_api.parser import load_ingresses
from analyzers.gateway_api.rules import build_rules


class GatewayApiAnalyzer(Analyzer):
    """Analyzes Ingress NGINX manifests for Gateway API migration readiness.

    Detects annotation portability issues, TLS/mTLS risks, and provides
    implementation profile context.
    """

    name = "gateway-api"
    version = "0.1.0"
    description = "Ingress NGINX → Gateway API migration intelligence"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        """Analyze an Ingress manifest file for Gateway API migration."""
        ingresses = load_ingresses(input_path)

        all_findings = []
        for ingress in ingresses:
            context = {
                "ingress_name": ingress["name"],
                "ingress_namespace": ingress["namespace"],
                "annotations": ingress["annotations"],
                "tls_hosts": ingress["tls_hosts"],
                "rules": ingress["rules"],
            }
            all_findings.extend(self.run_rules(context))

        metadata: dict[str, Any] = {
            "ingress_count": len(ingresses),
        }
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
        return list(self._rules)
