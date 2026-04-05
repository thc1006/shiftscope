"""Gateway API behavioral detection rules — cross-Ingress analysis.

These rules detect silent behavioral differences between ingress-nginx and
Gateway API that cause 404s and routing failures post-migration.

Source: Kubernetes blog "Before You Migrate" (2026-02-27) + community reports.
"""

from __future__ import annotations

from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule

_NGINX_PREFIX = "nginx.ingress.kubernetes.io/"


class RegexPrefixRule(Rule):
    """Behavior #1: Regex in nginx is prefix-based + case-insensitive, GW API is full + case-sensitive."""

    rule_id = "gw-behavior-regex-prefix"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("annotations", {}).get(f"{_NGINX_PREFIX}use-regex") == "true"

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        paths = context.get("paths", [])
        for p in paths:
            path_val = p.get("path", "")
            if not path_val:
                continue
            has_prefix_suffix = path_val.endswith(".*") or path_val.endswith(".*$")
            has_case_flag = "(?i)" in path_val
            if not has_prefix_suffix or not has_case_flag:
                issues = []
                if not has_prefix_suffix:
                    issues.append("missing '.*' suffix for prefix matching")
                if not has_case_flag:
                    issues.append("missing '(?i)' for case-insensitive matching")
                return Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    title="Regex behavior change: prefix + case-insensitive → full + case-sensitive",
                    detail=(
                        "ingress-nginx regex is prefix-based and case-insensitive. "
                        "Gateway API performs full case-sensitive matching. "
                        f"Issues: {', '.join(issues)}."
                    ),
                    evidence=f"{context.get('ingress_name', '?')}: path={path_val!r}",
                    recommendation="Add '.*' suffix and '(?i)' flag, or fix paths to exact case.",
                )
        return None


class RegexGlobalRule(Rule):
    """Behavior #2: use-regex applies globally per host across ALL Ingresses."""

    rule_id = "gw-behavior-regex-global"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("host_group"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        group = context.get("host_group", [])
        if len(group) < 2:
            return None
        regex_ingresses = [
            ig["name"]
            for ig in group
            if ig.get("annotations", {}).get(f"{_NGINX_PREFIX}use-regex") == "true"
        ]
        non_regex = [ig["name"] for ig in group if ig["name"] not in regex_ingresses]
        if regex_ingresses and non_regex:
            return Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                title="use-regex applies globally: sibling Ingresses silently affected",
                detail=(
                    f"Ingress(es) {regex_ingresses} have use-regex=true on this host. "
                    f"This silently converts ALL paths on Ingress(es) {non_regex} to regex mode. "
                    "In Gateway API, each HTTPRoute is independent — these paths will use their declared pathType."
                ),
                evidence=f"host={context.get('hostname', '?')}, regex={regex_ingresses}, affected={non_regex}",
                recommendation="Review affected Ingresses for paths that rely on implicit regex behavior.",
            )
        return None


class RewriteImpliesRegexRule(Rule):
    """Behavior #3: rewrite-target silently enables regex mode for entire host."""

    rule_id = "gw-behavior-rewrite-implies-regex"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("host_group"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        group = context.get("host_group", [])
        if len(group) < 2:
            return None
        rewrite_ingresses = [
            ig["name"]
            for ig in group
            if f"{_NGINX_PREFIX}rewrite-target" in ig.get("annotations", {})
        ]
        non_rewrite = [ig["name"] for ig in group if ig["name"] not in rewrite_ingresses]
        if rewrite_ingresses and non_rewrite:
            return Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                title="rewrite-target silently enables regex for entire host",
                detail=(
                    f"Ingress(es) {rewrite_ingresses} have rewrite-target on this host. "
                    "This implicitly enables regex mode for ALL paths on ALL Ingresses sharing this host. "
                    "Gateway API URLRewrite does NOT affect path matching on other HTTPRoutes."
                ),
                evidence=f"host={context.get('hostname', '?')}, rewrite={rewrite_ingresses}, affected={non_rewrite}",
                recommendation="Check sibling Ingresses for paths relying on implicit regex or case-insensitive matching.",
            )
        return None


class TrailingSlashRule(Rule):
    """Behavior #4: Missing trailing slash gets auto-301 in nginx, 404 in GW API."""

    rule_id = "gw-behavior-trailing-slash"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("paths"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        for p in context.get("paths", []):
            path_val = p.get("path", "")
            path_type = p.get("pathType", "")
            if path_type in ("Exact", "Prefix") and path_val.endswith("/") and path_val != "/":
                return Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    title="Trailing slash auto-redirect will not exist in Gateway API",
                    detail=(
                        "ingress-nginx auto-redirects '/path' → '/path/' with 301. "
                        "Gateway API does NOT configure any implicit redirects."
                    ),
                    evidence=f"{context.get('ingress_name', '?')}: path={path_val!r} pathType={path_type}",
                    recommendation="Add explicit RequestRedirect rule for the path without trailing slash.",
                )
        return None


class PathNormalizationRule(Rule):
    """Behavior #5: URL path normalization differs per implementation."""

    rule_id = "gw-behavior-path-normalization"
    severity = Severity.INFO

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("paths"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="URL path normalization may differ across Gateway API implementations",
            detail=(
                "ingress-nginx normalizes '.', '..', and '//' in paths. "
                "Gateway API implementations handle these differently, especially duplicate slashes."
            ),
            evidence=f"{context.get('ingress_name', '?')}: {len(context.get('paths', []))} path(s)",
            recommendation="Verify target Gateway implementation's path normalization documentation.",
        )


class SnippetNoEquivRule(Rule):
    """Behavior #7: configuration-snippet / server-snippet have NO Gateway API equivalent."""

    rule_id = "gw-behavior-snippet-no-equiv"
    severity = Severity.CRITICAL

    _SNIPPET_KEYS = (
        f"{_NGINX_PREFIX}configuration-snippet",
        f"{_NGINX_PREFIX}server-snippet",
    )

    def applies_to(self, context: dict[str, Any]) -> bool:
        return any(k in context.get("annotations", {}) for k in self._SNIPPET_KEYS)

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        annotations = context.get("annotations", {})
        found = [k.split("/")[-1] for k in self._SNIPPET_KEYS if k in annotations]
        if not found:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Snippet annotation(s) have NO Gateway API equivalent: {', '.join(found)}",
            detail=(
                "Raw NGINX directives injected via snippets cannot be portably represented "
                "in Gateway API. Requires complete re-architecture using native Gateway API "
                "filters or implementation-specific ExtensionPolicies."
            ),
            evidence=f"{context.get('ingress_name', '?')}: {', '.join(found)}",
            recommendation="Redesign using Gateway API HTTPRoute filters or implementation-specific extensions.",
        )


class CanaryRule(Rule):
    """Behavior #8: Canary annotations not directly translatable."""

    rule_id = "gw-behavior-canary"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return any(k.startswith(f"{_NGINX_PREFIX}canary") for k in context.get("annotations", {}))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        canary_keys = [
            k.split("/")[-1]
            for k in context.get("annotations", {})
            if k.startswith(f"{_NGINX_PREFIX}canary")
        ]
        if not canary_keys:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Canary annotations require different traffic-splitting approach",
            detail=(
                "ingress-nginx canary supports header/cookie/weight-based routing with specific precedence. "
                "Gateway API uses weight-based BackendRefs which has different semantics."
            ),
            evidence=f"{context.get('ingress_name', '?')}: {', '.join(canary_keys)}",
            recommendation="Redesign canary strategy using Gateway API HTTPRoute weight-based splitting.",
        )


class AffinityRule(Rule):
    """Behavior #9: Session affinity varies across implementations."""

    rule_id = "gw-behavior-affinity"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return f"{_NGINX_PREFIX}affinity" in context.get("annotations", {})

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        if f"{_NGINX_PREFIX}affinity" not in context.get("annotations", {}):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Session affinity support varies across Gateway API implementations",
            detail=(
                "ingress-nginx supports cookie-based affinity with 9+ sub-annotations. "
                "Gateway API support is implementation-dependent (experimental BackendTrafficPolicy)."
            ),
            evidence=f"{context.get('ingress_name', '?')}: affinity={context['annotations'][f'{_NGINX_PREFIX}affinity']}",
            recommendation="Verify target implementation supports session affinity before migration.",
        )


class HostMergeRule(Rule):
    """Behavior #10: Multiple Ingresses on same host have different merge/conflict rules."""

    rule_id = "gw-behavior-host-merge"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("host_group"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        group = context.get("host_group", [])
        if len(group) < 2:
            return None
        names = [ig["name"] for ig in group]
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"{len(group)} Ingresses share the same host — merge behavior differs in Gateway API",
            detail=(
                "ingress-nginx merges paths from multiple Ingresses for the same host. "
                "Gateway API has standardized conflict resolution: oldest HTTPRoute wins. "
                "Verify that path precedence matches expected behavior."
            ),
            evidence=f"host={context.get('hostname', '?')}, ingresses={names}",
            recommendation="Review path ordering and conflict resolution after migration.",
        )


def build_behavioral_rules() -> list[Rule]:
    """Build the behavioral detection rule set."""
    return [
        RegexPrefixRule(),
        RegexGlobalRule(),
        RewriteImpliesRegexRule(),
        TrailingSlashRule(),
        PathNormalizationRule(),
        SnippetNoEquivRule(),
        CanaryRule(),
        AffinityRule(),
        HostMergeRule(),
    ]
