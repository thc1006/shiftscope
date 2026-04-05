"""SARIF 2.1.0 renderer for ShiftScope reports.

Produces GitHub Code Scanning compatible SARIF output.
Severity mapping: critical→error, warning→warning, info→note.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from shiftscope import __version__
from shiftscope.core.models import Report, Severity

_SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cos02/schemas/sarif-schema-2.1.0.json"
)

_SEVERITY_TO_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}


def _to_sarif_uri(source: str) -> str:
    """Convert a source path to a SARIF-compatible URI."""
    path = PurePosixPath(source)
    if path.is_absolute():
        return f"file://{source}"
    return source


def render_sarif(report: Report, indent: int = 2) -> str:
    """Render a Report as SARIF 2.1.0 JSON string."""
    # Deduplicate rules by rule_id
    seen_rules: dict[str, dict[str, Any]] = {}
    for finding in report.findings:
        if finding.rule_id not in seen_rules:
            seen_rules[finding.rule_id] = {
                "id": finding.rule_id,
                "shortDescription": {"text": finding.title},
                "fullDescription": {"text": finding.detail},
                "defaultConfiguration": {
                    "level": _SEVERITY_TO_LEVEL.get(finding.severity, "warning"),
                },
                "helpUri": f"https://github.com/thc1006/shiftscope/blob/v{__version__}/README.md",
            }

    results = []
    for finding in report.findings:
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": _SEVERITY_TO_LEVEL.get(finding.severity, "warning"),
                "message": {
                    "text": f"{finding.title}: {finding.detail} Evidence: {finding.evidence}",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": _to_sarif_uri(report.source),
                            },
                        },
                    },
                ],
            }
        )

    sarif = {
        "$schema": _SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ShiftScope",
                        "version": __version__,
                        "informationUri": "https://github.com/thc1006/shiftscope",
                        "rules": list(seen_rules.values()),
                    },
                },
                "results": results,
            },
        ],
    }

    return json.dumps(sarif, indent=indent)
