"""MCP Security vulnerability detection rules.

Detects the top vulnerability patterns from Endor Labs (2,614 implementations)
and Astrix (5,200+ implementations) surveys. Maps to OWASP ASI categories.
"""

from __future__ import annotations

import re
from typing import Any

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule

_SECRET_PATTERNS = re.compile(
    r"(sk-live|sk-proj|ghp_|gho_|github_pat_|xoxb-|xoxp-|AKIA[A-Z0-9]"
    r"|eyJ[a-zA-Z0-9]|glpat-|Bearer\s)",
    re.IGNORECASE,
)
_SECRET_KEY_NAMES = re.compile(r"(api[_-]?key|secret|token|password|pat|credential)", re.IGNORECASE)
_SHELL_COMMANDS = {"mcp_shell_server", "shell_server", "exec_server", "run_command"}
_DANGEROUS_ARGS = {"--allow-all", "--no-sandbox", "--unsafe", "-y"}


class StaticCredentialsRule(Rule):
    """Detects plaintext API keys, tokens, or secrets in MCP server env vars."""

    rule_id = "mcp-sec-static-credentials"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("env"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        env = context.get("env", {})
        exposed = []
        for key, value in env.items():
            if _SECRET_KEY_NAMES.search(key) or _SECRET_PATTERNS.search(str(value)):
                exposed.append(key)
        if not exposed:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title=f"Plaintext credentials in MCP server config: {', '.join(exposed)}",
            detail=(
                "Static API keys and tokens in environment variables are long-lived, "
                "rarely rotated, and exposed to any process with env access. "
                "53% of MCP servers use static credentials (Astrix survey). [OWASP ASI-03]"
            ),
            evidence=f"server={context.get('server_name', '?')}, keys={exposed}",
            recommendation="Use a secret vault (HashiCorp Vault, AWS Secrets Manager) with runtime injection.",
        )


class MissingAuthRule(Rule):
    """Detects MCP servers with no authentication configured."""

    rule_id = "mcp-sec-missing-auth"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return True

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        auth = context.get("auth")
        if auth and auth.get("type"):
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="MCP server has no authentication configured",
            detail=(
                "Without authentication, any network-reachable client can invoke tools. "
                "CVE-2026-32211 (Azure MCP Server, CVSS 9.1) had zero authentication. [OWASP ASI-03]"
            ),
            evidence=f"server={context.get('server_name', '?')}, auth=none",
            recommendation="Implement OAuth 2.1 with PKCE. For local-only, use stdio transport.",
        )


class OverPermissionRule(Rule):
    """Detects servers with wildcard or overly broad permissions."""

    rule_id = "mcp-sec-over-permission"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("env") or context.get("args"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        env = context.get("env", {})
        args = context.get("args", [])
        issues = []
        for key, val in env.items():
            if str(val).strip() == "*":
                issues.append(f"env.{key}=*")
        for arg in args:
            if arg in _DANGEROUS_ARGS:
                issues.append(f"arg={arg}")
        if not issues:
            return None
        return Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            title="MCP server has overly broad permissions",
            detail=(
                "Wildcard permissions or unsafe flags grant unrestricted access. "
                "Principle of least privilege requires scoped permissions per tool. [OWASP ASI-03]"
            ),
            evidence=f"server={context.get('server_name', '?')}, issues={issues}",
            recommendation="Replace wildcards with explicit allowlists of permitted operations.",
        )


class CommandInjectionRule(Rule):
    """Detects MCP servers that run shell commands (command injection risk)."""

    rule_id = "mcp-sec-command-injection"
    severity = Severity.CRITICAL

    def applies_to(self, context: dict[str, Any]) -> bool:
        return bool(context.get("command") or context.get("args"))

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        args = context.get("args", [])
        args_str = " ".join(str(a) for a in args).lower()
        if any(name in args_str for name in _SHELL_COMMANDS):
            return Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                title="MCP server exposes shell/command execution",
                detail=(
                    "Shell-executing MCP servers are the primary vector for command injection. "
                    "34% of MCP implementations use sensitive APIs tied to command injection. [OWASP ASI-05]"
                ),
                evidence=f"server={context.get('server_name', '?')}, args={args}",
                recommendation="Remove shell access or sandbox with strict argument allowlisting.",
            )
        return None


class SupplyChainRule(Rule):
    """Detects unpinned package installations (npx -y without version)."""

    rule_id = "mcp-sec-supply-chain"
    severity = Severity.WARNING

    def applies_to(self, context: dict[str, Any]) -> bool:
        return context.get("command") in ("npx", "uvx", "pipx")

    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        args = context.get("args", [])
        # Check for -y flag (auto-install without confirmation)
        has_auto_install = "-y" in args or "--yes" in args
        # Check if package has version pin
        pkg_args = [a for a in args if not a.startswith("-")]
        has_version = any("@" in a and not a.startswith("@") or a.count("@") > 1 for a in pkg_args)
        if has_auto_install and not has_version:
            return Finding(
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                title="Unpinned MCP server package installation",
                detail=(
                    "Auto-installing packages without version pins enables supply chain attacks "
                    "via typosquatting or package hijacking. mcp-remote (558K+ downloads) "
                    "had CVE-2025-6514. [OWASP ASI-04]"
                ),
                evidence=f"server={context.get('server_name', '?')}, {context.get('command', '?')} auto-install without version pin",
                recommendation="Pin specific package versions: e.g., @scope/package@1.2.3",
            )
        return None


def build_rules() -> list[Rule]:
    """Build the MCP security rule set."""
    return [
        StaticCredentialsRule(),
        MissingAuthRule(),
        OverPermissionRule(),
        CommandInjectionRule(),
        SupplyChainRule(),
    ]
