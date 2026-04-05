"""Gateway API migration rules — annotation analysis and TLS risk detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule

_CONFIGS_DIR = Path(__file__).parent / "configs"


def _is_nginx_annotation(key: str) -> bool:
    """Check if a Kubernetes annotation key belongs to the nginx ingress controller.

    This checks a Kubernetes annotation key prefix, not a URL.
    The prefix 'nginx.ingress.kubernetes.io/' is a standard K8s annotation
    namespace, not a web URL despite containing dots and slashes.
    """
    parts = key.split("/", 1)
    return len(parts) == 2 and parts[0] == "nginx.ingress.kubernetes.io"


_SEVERITY_MAP = {
    "info": Severity.INFO,
    "medium": Severity.WARNING,
    "high": Severity.WARNING,  # ShiftScope has 3 levels; high maps to warning
    "critical": Severity.CRITICAL,
}


def _load_annotation_mappings() -> dict[str, dict]:
    with open(_CONFIGS_DIR / "annotation_mappings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# --- Annotation rules ---


class AnnotationRule(Rule):
    """Rule for a specific known Ingress NGINX annotation."""

    rule_id = "gw-annotation-placeholder"  # Overridden per-instance in __init__
    severity = Severity.WARNING  # Overridden per-instance in __init__

    def __init__(self, annotation_key: str, mapping: dict):
        self._annotation_key = annotation_key
        self._mapping = mapping
        short_name = annotation_key.split("/")[-1]
        self.rule_id = f"gw-annotation-{short_name}"
        self.severity = _SEVERITY_MAP.get(mapping["severity"], Severity.WARNING)

    def applies_to(self, context: dict[str, Any]) -> bool:
        return self._annotation_key in context.get("annotations", {})

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        annotations = context.get("annotations", {})
        if self._annotation_key not in annotations:
            return None
        value = annotations[self._annotation_key]
        ns = context.get("ingress_namespace", "?")
        name = context.get("ingress_name", "?")
        suggested = self._mapping.get("suggested_feature")
        rec = f"Use {suggested}." if suggested else "Manual redesign required."
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Annotation '{self._annotation_key.split('/')[-1]}' detected",
            detail=self._mapping["rationale"],
            evidence=f"{ns}/{name}: {self._annotation_key}={value!r}",
            recommendation=rec,
        )


class UnknownAnnotationRule(Rule):
    """Catches nginx.ingress.kubernetes.io/* annotations not in the curated mapping."""

    rule_id = "gw-annotation-unknown"
    severity = Severity.WARNING

    def __init__(self, known_keys: set[str]):
        self._known_keys = known_keys

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("annotations"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        annotations = context.get("annotations", {})
        # This is a Kubernetes annotation key prefix (e.g., "nginx.ingress.kubernetes.io/enable-cors"),
        # NOT a URL being sanitized. CodeQL py/incomplete-url-substring-sanitization is a false positive.
        unknown = [
            k for k in sorted(annotations) if _is_nginx_annotation(k) and k not in self._known_keys
        ]
        if not unknown:
            return None
        ns = context.get("ingress_namespace", "?")
        name = context.get("ingress_name", "?")
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"{len(unknown)} unmapped annotation(s) detected",
            detail="No curated mapping exists. Manual review required.",
            evidence=f"{ns}/{name}: {', '.join(unknown)}",
            recommendation="Review Gateway API equivalent for each annotation.",
        )


# --- TLS risk rules ---


class WildcardTLSRule(Rule):
    """Detects wildcard TLS hosts that may cause certificate/listener issues."""

    rule_id = "gw-tls-wildcard"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("tls_hosts"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        wildcards = [h for h in context.get("tls_hosts", []) if "*" in h]
        if not wildcards:
            return None
        ns = context.get("ingress_namespace", "?")
        name = context.get("ingress_name", "?")
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Wildcard TLS host detected",
            detail="Wildcard TLS hosts require ListenerSet review; verify certificate overlap and listener/port strategy to avoid HTTP/2 coalescing surprises.",
            evidence=f"{ns}/{name}: tls_hosts={wildcards}",
            recommendation="Review certificate overlap and listener strategy.",
        )


class FrontendMTLSRule(Rule):
    """Detects frontend mTLS configuration that needs Gateway API review."""

    rule_id = "gw-tls-frontend-mtls"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "nginx.ingress.kubernetes.io/auth-tls-secret" in context.get("annotations", {})

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        annotations = context.get("annotations", {})
        key = "nginx.ingress.kubernetes.io/auth-tls-secret"
        if key not in annotations:
            return None
        ns = context.get("ingress_namespace", "?")
        name = context.get("ingress_name", "?")
        secret = annotations[key]
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Frontend mTLS configuration detected",
            detail="auth-tls-secret suggests frontend mTLS; review Gateway API client certificate validation and HTTP/2 connection coalescing boundaries.",
            evidence=f"{ns}/{name}: auth-tls-secret={secret!r}",
            recommendation="Review Gateway client certificate validation configuration.",
        )


class BackendProtocolRule(Rule):
    """Detects backend protocol hints that may require TLS origination."""

    rule_id = "gw-tls-backend-protocol"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return "nginx.ingress.kubernetes.io/backend-protocol" in context.get("annotations", {})

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        annotations = context.get("annotations", {})
        key = "nginx.ingress.kubernetes.io/backend-protocol"
        if key not in annotations:
            return None
        ns = context.get("ingress_namespace", "?")
        name = context.get("ingress_name", "?")
        proto = annotations[key]
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Backend protocol hint detected",
            detail="Backend protocol hints often imply TLS origination or backend identity requirements that need explicit Gateway API configuration.",
            evidence=f"{ns}/{name}: backend-protocol={proto!r}",
            recommendation="Validate whether TLS origination or BackendTLSPolicy is required.",
        )


def build_rules() -> list[Rule]:
    """Build the complete rule set for Gateway API migration analysis."""
    mappings = _load_annotation_mappings()
    rules: list[Rule] = []

    # One rule per known annotation
    for key, mapping in mappings.items():
        rules.append(AnnotationRule(key, mapping))

    # Unknown annotation catcher
    rules.append(UnknownAnnotationRule(known_keys=set(mappings.keys())))

    # TLS risk rules
    rules.append(WildcardTLSRule())
    rules.append(FrontendMTLSRule())
    rules.append(BackendProtocolRule())

    return rules
