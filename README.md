# ShiftScope

**Migration intelligence for cloud-native infrastructure.**

[![CI](https://github.com/thc1006/shiftscope/actions/workflows/ci.yml/badge.svg)](https://github.com/thc1006/shiftscope/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)

ShiftScope is a pluggable framework for building **migration intelligence analyzers** for Kubernetes infrastructure API transitions. Unlike API version detectors (Pluto, kubent) that only flag deprecated `apiVersion` strings, or format converters (ingress2gateway) that only transform YAML, ShiftScope provides **semantic risk analysis**, **implementation matching**, and **structured migration findings** through a pluggable analyzer SDK.

## Why ShiftScope?

| Tool | Detection | Conversion | Risk Analysis | MCP | Pluggable SDK |
|------|-----------|------------|---------------|-----|---------------|
| Pluto / kubent | apiVersion only | - | - | - | - |
| ingress2gateway | - | YAML transform | - | - | - |
| Konveyor AI | app code | app code | app-layer | partial | - |
| **ShiftScope** | **semantic** | - | **annotations, TLS, feature gates** | **native** | **yes** |

## Quick Start

```bash
# Install
pip install shiftscope[cli]

# List available analyzers
shiftscope list

# Analyze an Ingress manifest for Gateway API migration
shiftscope analyze gateway-api examples/ingress-nginx/basic.yaml --output markdown

# Analyze a NetworkIntent for DRA migration
shiftscope analyze dra-network examples/dra-network-intent.json --output json

# Analyze a Helm chart for v4 readiness
shiftscope analyze helm4-readiness examples/helm-sample-app/ --output markdown
```

## Built-in Analyzers

### Gateway API (`gateway-api`)
Ingress NGINX → Gateway API migration intelligence.
- 5 annotation portability rules (CORS, backend-protocol, auth-tls-secret, server-snippet, ssl-redirect)
- 3 TLS risk rules (wildcard TLS, frontend mTLS/coalescing, backend protocol)
- 1 unknown annotation catcher
- 6 implementation profiles (Envoy Gateway, NGINX Gateway Fabric, Cilium, Kong, Contour, Traefik)

### DRA Networking (`dra-network`)
Device Plugin → Dynamic Resource Allocation migration intelligence.
- Alpha feature gate detection (extended_resource_mapping, consumable_capacity, partitionable_devices)
- RDMA/bandwidth requirements analysis
- Legacy bridge (SR-IOV/Multus) migration path detection
- Topology alignment (NUMA/PCI) requirements
- Workload kind validation

### Helm 4 Readiness (`helm4-readiness`)
Helm 3 → Helm 4 / Charts v3 readiness analysis.
- Chart API v2 detection with v3 migration guidance
- Go template complexity analysis
- Resource sequencing needs (HIP-0025)
- .helmignore parity review
- Values parent/subchart transform detection

### Telco Intent (`telco-intent`)
Telco YANG → GitOps intent provenance analysis.
- GitOps target validation (Flux/Nephio K8s version conflict)
- Provenance review (hydration/IPAM fields need human review)
- SDC southbound contract-only warning

### Agent Readiness (`agent-readiness`)
AI agent pilot → production readiness assessment.
- Tool allowlist compliance (blocks unapproved tools)
- Token budget enforcement
- Observability gating (OTEL + trace coverage >= 80%)
- Weighted promotion gate (security 0.4 + observability 0.35 + economics 0.25)

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 ShiftScope SDK                    │
│                                                  │
│  Core Models ─── Renderers ─── Eval Harness      │
│  (Pydantic)      (JSON/MD)    (golden-file)      │
│                                                  │
│  Rule ABC ────── Analyzer ABC ── Registry        │
│  (applies_to     (run_rules)    (entry_points    │
│   + evaluate)                    discovery)       │
│                                                  │
│  CLI ─────────── MCP Bridge ─── AI Augment       │
│  (Typer,          (FastMCP,      (PydanticAI,    │
│   auto-gen)        auto-gen)      optional)      │
│                                                  │
│  MCP Discovery ── A2A Agent Card                 │
│  (.well-known)    (capabilities)                 │
└──────────────────────────────────────────────────┘
     │          │          │          │          │
 Gateway    DRA        Helm 4    Telco      Agent
 API        Network    Readiness Intent     Readiness
```

## Writing a Custom Analyzer

```python
from shiftscope import Analyzer, Rule, Finding, Severity, Report

class MyRule(Rule):
    rule_id = "my-check"
    severity = Severity.WARNING

    def applies_to(self, context):
        return "config" in context

    def evaluate(self, context):
        if context["config"].get("deprecated_field"):
            return Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                title="Deprecated field detected",
                detail="This field is removed in the next version.",
                evidence=f"deprecated_field={context['config']['deprecated_field']}",
                recommendation="Migrate to the new field.",
            )
        return None

class MyAnalyzer(Analyzer):
    name = "my-analyzer"
    version = "0.1.0"
    description = "Custom migration analyzer"

    def __init__(self):
        self._rules = [MyRule()]

    def analyze(self, input_path, **kwargs):
        context = {"config": load_config(input_path)}
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=self.run_rules(context),
        )

    def list_rules(self):
        return list(self._rules)
```

Register via entry points in your `pyproject.toml`:
```toml
[project.entry-points."shiftscope.analyzers"]
my-analyzer = "my_package:MyAnalyzer"
```

## MCP Integration

ShiftScope exposes all analyzers as MCP tools for AI agent consumption:

```python
from shiftscope.mcp.bridge import create_mcp_server
from shiftscope.core.analyzer import AnalyzerRegistry

registry = AnalyzerRegistry()
registry.discover()
server = create_mcp_server(registry)
server.run()  # Exposes analyze_gateway_api, analyze_dra_network, etc.
```

## Development

```bash
git clone https://github.com/thc1006/shiftscope.git
cd shiftscope
make bootstrap    # requires uv
make test         # 193 tests
make lint         # ruff check
make verify       # lint + test + compileall
```

## Roadmap

See [ADR-001](docs/adr/001-unified-migration-intelligence-sdk.md) for the full architectural decision record, cross-validation results, and phase-by-phase roadmap.

| Phase | Status | Scope |
|-------|--------|-------|
| 1: Core SDK + Reference Analyzer | Done | Models, Rule/Analyzer ABC, renderers, CLI, MCP bridge, Gateway API analyzer |
| 2: Multi-Analyzer + CI | Done | DRA + Helm 4 analyzers, GitHub Actions CI, CodeQL |
| 3: AI Augmentation | Done | Telco + agent readiness analyzers, PydanticAI, A2A |
| 4: CNCF Sandbox | Planned | Landscape listing, TAG presentation, Sandbox proposal |
| 5: Ecosystem | Planned | GitHub Action, Argo Workflows, KubeCon NA 2026 |

## License

[Apache License 2.0](LICENSE)
