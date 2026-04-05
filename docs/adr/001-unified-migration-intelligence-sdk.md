# ADR-001: ShiftScope — Unified Migration Intelligence SDK for Cloud-Native Infrastructure

- **Status:** CROSS-VALIDATED (2026-04-05, 5 parallel research tracks completed)
- **Date:** 2026-04-05
- **Author:** thc1006
- **Deciders:** thc1006

## Context

### Problem Statement

Kubernetes infrastructure API deprecation is a **recurring, high-cost, structurally unsolved problem**.

Every 3–4 releases, the Kubernetes project deprecates and removes APIs, forcing platform teams into migration campaigns. Historical evidence:

| Event | Impact |
|-------|--------|
| K8s v1.22 "Great Beta API Purge" (2021) | Largest single-version API removal in K8s history |
| PodSecurityPolicy removal (v1.25, 2022) | Months of migration work for teams; PSA is non-mutating unlike PSP |
| In-tree cloud provider removal (v1.31, 2024) | 1.5M lines of code removed; described as "the largest migration in K8s history" |
| Ingress NGINX retirement (2026-03-24) | Affects ~50% of K8s clusters; controller made read-only, no more security patches |
| Device Plugin → DRA (v1.34 GA, v1.35 stable) | Entire device allocation model redesigned; networking extensions still alpha |
| Helm 3 → Helm 4 (v4.0.0 released 2025-11) | OCI-only registry, Charts v3 scaffolding, new plugin system |
| Endpoints API deprecated (v1.33) | Migrating to EndpointSlice |
| cgroup v1 removed (v1.35) | Infrastructure-level change, kubelet refuses to start |

Industry data confirms the pain:
- 65% of cloud migration projects stall or fail due to poor planning (Forrester)
- 38% exceed budget, averaging 23% overruns (IDC)
- Cloud migration services market: $31.5B in 2026 at 22.4% CAGR
- Google internal research (FSE 2025): LLM-assisted migration reduces time by 50%

### Existing Tool Landscape (as of 2026-04, cross-validated)

#### Tier 1: Detection-Only Tools

| Tool | What It Does | What It Does NOT Do |
|------|-------------|---------------------|
| **Pluto** (FairwindsOps) | Detects deprecated `apiVersion` strings in YAML/Helm/live clusters | No semantic analysis, no risk assessment, no migration planning |
| **kubent** (DoiT) | Flags deprecated API versions via embedded Rego rules | Same limitations; Rego rules are GVK pattern matching only |
| **Silver Surfer** (Devtron, **CNCF Sandbox**) | Validates K8s objects against OpenAPI specs; provides migration paths | No semantic risk analysis, no MCP, not an SDK, K8s core APIs only |
| **KubePug** | Pre-upgrade checker using OpenAPI spec validation | Detection only, no intelligence layer |

#### Tier 2: Single-Domain Converters

| Tool | What It Does | What It Does NOT Do |
|------|-------------|---------------------|
| **ingress2gateway** (k8s-sigs, v1.0) | Converts Ingress YAML → Gateway API YAML (30+ annotations) | Format conversion only; no TLS risk, no implementation matching, no MCP |
| **ing-switch** (2026, new) | Maps 119 Ingress annotations with impact ratings (NONE/LOW/MEDIUM) | Single domain (Ingress only), no SDK, no MCP, no semantic analysis |

#### Tier 3: Application-Layer Migration

| Tool | What It Does | What It Does NOT Do |
|------|-------------|---------------------|
| **Konveyor** (CNCF Sandbox, v0.8.0) | Application modernization (Java/VM → K8s) | Application-layer only; does NOT do infrastructure API migration |
| **Konveyor AI (Kai)** | LLM + MCP solution server for code migration; published Ingress→GW API blog (2026-03) | Targets application **source code** (Go, Java), not infrastructure YAML manifests |

#### Tier 4: Vendor-Locked Solutions

| Tool | What It Does | What It Does NOT Do |
|------|-------------|---------------------|
| **MS Container-Migration-Solution-Accelerator** | Multi-agent AI migration analysis with MCP; most technically similar to ShiftScope | Azure-locked, monolithic app (not an SDK), not vendor-neutral, not pluggable |
| **Azure Copilot Migration Agent** | VM → Azure migration | Vendor-locked, not K8s API migration |
| **AWS Transform** | Mainframe modernization | Vendor-locked, not K8s API migration |
| **AWS EKS Upgrade Insights** | Scans audit logs for deprecated API usage | Detection only, EKS-specific, no SDK |
| **GKE Deprecation Insights** | Pauses auto-upgrades on deprecated features | Detection only, GKE-specific, no SDK |

### The Gap

```
                       Application Migration       Infrastructure API Migration
                       ─────────────────────       ────────────────────────────
API Version Detection   ─                          Pluto, kubent, Silver Surfer ✅
Format Conversion       Move2Kube, Konveyor        ingress2gateway, ing-switch ✅
Semantic Analysis +     Konveyor AI (app-layer)     MS Solution Accelerator (Azure-only)
Risk Assessment +       ─                           ← NO VENDOR-NEUTRAL SDK
Migration Planning +
MCP Exposure +
Cross-Domain SDK
```

No existing tool provides a **vendor-neutral, pluggable SDK** for infrastructure API migration intelligence that combines **semantic risk analysis** with **MCP exposure** as composable primitives. The closest approaches are: (1) Microsoft's Container-Migration-Solution-Accelerator, which provides AI-driven migration analysis with MCP integration but is Azure-locked, monolithic, and not reusable as a library; (2) Konveyor KAI, which includes an MCP solution server and static analysis-driven migration but targets application source code rather than infrastructure API transitions; and (3) the detection-only tools (Pluto, kubent, Silver Surfer, KubePug) which identify deprecations but provide no semantic risk scoring or migration intelligence.

### Grounding Evidence

This ADR is grounded in 6 prototype projects built after attending KubeCon + CloudNativeCon Europe 2026 (Amsterdam, March 23-26, 2026). Each project was inspired by a specific session and independently developed the same architectural pattern:

| Project | KubeCon Session | Domain |
|---------|----------------|--------|
| gateway-migration-orchestrator | "Gateway API: Bridging the Gap from Ingress to the Future" | Ingress → Gateway API |
| netintent-dra-bridge-v2 | "Kubernetes Network Driver Unpacked" | Device Plugin → DRA |
| telco-intent-provenance-lab | "From YANG To YAML: How We Tamed the 5G Configuration Beast" | YANG/NETCONF → GitOps |
| helmforge-lab-m2 | "Helm 4 Is Here. So, Now What?" | Helm 3 → Helm 4 |
| agent-readiness-lab | "Day-2 Ready" + "Rescue Agents From Prototype Purgatory" | Agent pilot → production |
| agent-readiness-gate | Same agentic sessions | Agent readiness gating |

All 6 independently converged on:
1. Deterministic-first, AI-optional analysis
2. Structured findings with rule_id, severity, evidence, recommendation
3. MCP server exposure for AI agent consumption
4. CLI as primary interface
5. Golden-file evaluation framework
6. CPU-only MVP with optional GPU sidecar path
7. Identical 10-document research pipeline (00-09)

This convergence validates that the pattern is generalizable into an SDK.

### CNCF Ecosystem Alignment

- **CNCF has 230+ projects, 300K+ contributors** (2026-01 annual report)
- **AI is the hottest category**: kagent, HolmesGPT, llm-d, KAITO, KAI Scheduler, Higress all accepted 2025-2026
- **CNCF "Cloud-Native Foundations for Distributed Agentic Systems" initiative** (cncf/toc#1746): focuses on MCP, agentic gateways, agent runtime — ShiftScope fits directly
- **No dedicated Migration SIG or TAG**: migration responsibility scattered across SIG-Network, SIG-Auth, SIG-Storage, SIG-Node, SIG-API-Machinery
- **MCP adoption**: 97M+ monthly SDK downloads; kubernetes-mcp-server, ToolHive, kagent all integrating MCP
- **TAG restructuring (May 2025)**: 5 new TAGs; ShiftScope fits under TAG Infrastructure or TAG Developer Experience
- **Konveyor contributor decline**: -33% YoY, still at Sandbox after 4 years — indicates the app-migration angle alone is insufficient

## Decision

**Build ShiftScope: a pluggable migration intelligence SDK for cloud-native infrastructure API transitions.**

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ShiftScope SDK                        │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Core     │  │  Render  │  │  MCP     │  │  CLI   │  │
│  │  Models   │  │  Engine  │  │  Bridge  │  │  App   │  │
│  │          │  │          │  │          │  │        │  │
│  │ Finding  │  │ JSON     │  │ Auto-gen │  │ Auto-  │  │
│  │ Report   │  │ Markdown │  │ MCP tools│  │ gen    │  │
│  │ Severity │  │          │  │ from     │  │ CLI    │  │
│  │ Rule     │  │          │  │ analyzers│  │ from   │  │
│  │ Analyzer │  │          │  │          │  │ analyz.│  │
│  │ Profile  │  │          │  │          │  │        │  │
│  │ Registry │  │          │  │          │  │        │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│                                                         │
│  ┌──────────┐                                           │
│  │  Eval    │                                           │
│  │  Harness │  Golden-file testing for analyzers        │
│  └──────────┘                                           │
└─────────────────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │ Gateway │   │  DRA    │   │  Helm 4 │   ...
    │ API     │   │ Network │   │ Charts  │
    │ Analyzer│   │ Analyzer│   │ v3 Anal.│
    └─────────┘   └─────────┘   └─────────┘
    (Reference implementations / plugins)
```

### Core Abstractions

Data models use **Pydantic BaseModel** (not dataclasses) for JSON Schema generation, validation, serialization, and MCP integration. Behavioral contracts use **ABC**.

```python
# 1. Finding — the atomic unit of analysis output (Pydantic BaseModel)
class Finding(BaseModel):
    rule_id: str           # e.g., "gw-tls-coalescing-risk"
    severity: Severity     # info | warning | critical
    title: str             # Human-readable title
    detail: str            # Explanation
    evidence: str          # What triggered this finding
    recommendation: str    # What to do about it

# 2. Report — aggregated output of an analyzer run (Pydantic BaseModel)
class Report(BaseModel):
    analyzer_name: str
    analyzer_version: str
    source: str            # What was analyzed
    findings: list[Finding]
    metadata: dict[str, Any] = {}

# 3. Rule — a single analysis rule (ABC for behavioral contract)
class Rule(ABC):
    rule_id: str
    severity: Severity
    def applies_to(self, context: dict[str, Any]) -> bool  # short-circuit (Kyverno-inspired)
    def evaluate(self, context: dict[str, Any]) -> Finding | None

# 4. Analyzer — a collection of rules for a migration domain (ABC)
class Analyzer(ABC):
    name: str
    version: str
    description: str
    def analyze(self, input_path: str, **kwargs) -> Report
    def list_rules(self) -> list[Rule]

# 5. AnalyzerRegistry — plugin discovery via importlib.metadata.entry_points
class AnalyzerRegistry:
    def register(self, analyzer: Analyzer) -> None
    def get(self, name: str) -> Analyzer
    def list_all(self) -> list[Analyzer]
    def discover(self, group: str = "shiftscope.analyzers") -> None  # entry_points
```

**Design rationale (cross-validated):**
- **Pydantic > dataclasses** for Finding/Report: JSON Schema via `model_json_schema()` enables MCP tool schema auto-generation; validation catches typos (e.g., `severity="critcal"`); `model_dump_json()` replaces manual serialization; FastMCP natively generates richer schemas from Pydantic models.
- **ABC > Protocol** for Rule/Analyzer: explicit opt-in via inheritance; runtime enforcement via `@abstractmethod`; plugin authors must intentionally implement the contract.
- **`applies_to()` on Rule**: inspired by Kyverno's match/exclude pattern; enables short-circuit skipping of irrelevant rules without running full evaluation.
- **`importlib.metadata.entry_points`**: standard library (Python 3.12), zero dependencies, same pattern as MkDocs and pytest plugin discovery.

### Technology Choices (cross-validated 2026-04-05)

#### Core Dependencies (minimum bounds for SDK, exact pins in uv.lock)

| Choice | Selected | Rationale |
|--------|----------|-----------|
| **Language** | Python >=3.12,<3.14 | All 6 prototypes are Python; MCP SDK, PydanticAI, OpenAI Agents SDK all Python-first; AI/ML ecosystem dominant |
| **Data validation** | Pydantic >=2.10 | JSON Schema generation, validation, serialization; FastMCP/PydanticAI native |
| **YAML parsing** | PyYAML >=6.0 | K8s manifests are YAML |
| **Templating** | Jinja2 >=3.1 | Markdown report rendering |

#### Optional Dependencies (extras)

| Extra | Packages | Purpose |
|-------|----------|---------|
| `cli` | Typer >=0.12, Rich >=13 | CLI interface with formatted output |
| `mcp` | mcp[cli] >=1.20 | MCP server exposure (FastMCP built-in) |
| `ai` | PydanticAI >=1.70 | Optional AI augmentation |
| `full` | All of the above | Full installation |

#### Dev Dependencies (PEP 735 dependency-groups, NOT extras)

| Group | Packages | Purpose |
|-------|----------|---------|
| `dev` | Ruff >=0.15, pre-commit >=4.5 | Linting, formatting |
| `test` | pytest >=9, pytest-cov >=7, Hypothesis >=6.100, syrupy >=4 | Testing, property-based testing, snapshot/golden-file |

#### Build & Tooling

| Choice | Selected | Rationale |
|--------|----------|-----------|
| **Build backend** | hatchling | PyPA-maintained, plugin support, entry_point aware |
| **Package manager** | uv >=0.11 | 10-100x faster than pip; lockfile (uv.lock) for reproducibility |
| **License** | Apache 2.0 | CNCF requirement |

#### MCP Architecture (cross-validated)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **MCP SDK** | Official `mcp` v1.27.0 with built-in FastMCP | Stable; spec version 2025-11-25 |
| **Transport (remote)** | Streamable HTTP | Recommended by MCP spec; stateless, supports horizontal scaling |
| **Transport (local)** | stdio | Security isolation; MCP spec recommended for local servers |
| **Transport (avoid)** | SSE | Deprecated; Atlassian removal date 2026-06-30 |
| **Discovery** | `.well-known/mcp/server.json` | Emerging standard (SEP-1649, SEP-1960); GitHub MCP Registry compatible |
| **A2A protocol** | Deferred to Phase 3+ | Complementary to MCP (not competing); AAIF governs both; not needed until agent-to-agent collaboration |
| **Auth** | OAuth 2.1 with PKCE | MCP spec standard; progressive scope elevation |

#### Plugin Discovery

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Mechanism** | `importlib.metadata.entry_points(group='shiftscope.analyzers')` | Standard library, zero dependencies; same pattern as MkDocs/pytest |
| **Interface** | ABC (not Protocol) | Explicit opt-in, runtime enforcement via @abstractmethod |
| **Rule engine** | Custom Python ABC (not OPA/Rego/CEL) | Semantic analysis requires full Python expressiveness; no existing engine fits (validated against 7 alternatives) |
| **CEL support** | Phase 2+ optional | Kubescape 4.0 migrated Rego→CEL; useful for simple declarative rules alongside Python |

### Design Principles

1. **Deterministic-first**: Core analysis is rule-based and reproducible. LLM is optional augmentation, never in the authority path.
2. **Pluggable analyzers**: Each migration domain is a separate analyzer plugin. The SDK provides the scaffold; plugins provide the domain logic.
3. **MCP-native**: Every analyzer automatically gets MCP tool exposure. AI agents can discover and invoke analysis without custom integration.
4. **CPU-only MVP**: No GPU required for core analysis. GPU is optional for AI augmentation sidecar.
5. **Structured findings**: Every output is typed, machine-readable, and actionable. No free-text-only reports.
6. **Golden-file evaluation**: Every analyzer ships with eval cases and golden outputs for regression testing.
7. **Research-grounded**: Architectural decisions traceable to official sources, not speculation.

### Phase 1 Scope (MVP)

| Component | Deliverable |
|-----------|-------------|
| Core models | Finding, Report, Severity, Rule ABC, Analyzer ABC, AnalyzerRegistry |
| JSON renderer | `Report → JSON` |
| Markdown renderer | `Report → Markdown` |
| Eval harness | Golden-file test runner |
| CLI scaffolding | Auto-generate CLI from registered analyzers |
| MCP bridge | Auto-generate MCP tools from registered analyzers |
| Gateway API analyzer | Reference implementation ported from gateway-migration-orchestrator |
| Tests | 100% coverage on core SDK; reference analyzer tests |
| Governance | LICENSE, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, MAINTAINERS.md |
| Documentation | README, ADR-001 |

### Future Phases

| Phase | Scope |
|-------|-------|
| **Phase 2** | DRA networking analyzer; Helm 4 analyzer; analyzer plugin discovery via entry points |
| **Phase 3** | Telco intent analyzer; agent readiness analyzer; optional PydanticAI augmentation |
| **Phase 4** | CRD/Operator layer for K8s-native deployment; CNCF Sandbox proposal |
| **Phase 5** | CI/CD integration; GitHub Action; Argo Workflows integration |

## Alternatives Considered

### A. Extend Konveyor

**Rejected.** Konveyor is designed for application-layer modernization (Java code analysis, VM-to-container). Its architecture (Windup/Kantra rule engine, Java/Go codebase) is not suited for infrastructure API semantic analysis. Konveyor's contributor base is declining (-33% YoY). Building on top would require fighting the existing architecture.

### B. Extend Pluto/kubent

**Rejected.** These are API version detectors, not semantic analyzers. Adding risk assessment, implementation matching, and MCP would require a complete rewrite. They also lack plugin architecture for cross-domain support.

### C. Build domain-specific tools (status quo)

**Rejected.** This is what the 6 prototypes already demonstrate — each migration domain gets its own tool. The problem: shared infrastructure (CLI, MCP, eval, rendering) is reimplemented 6 times. An SDK eliminates this duplication while preserving domain specialization.

### D. Build a Kubernetes Operator / CRD-based system

**Deferred to Phase 4.** The core value is in the analysis logic, not in the deployment model. Starting with a Python SDK maximizes iteration speed and accessibility. A K8s-native layer can be added later for production deployment.

### E. Use Go instead of Python

**Rejected for Phase 1.** While CNCF ecosystem favors Go, the AI/ML ecosystem (MCP, PydanticAI, OpenAI Agents SDK, vLLM) is Python-first. All 6 prototypes are Python. The analysis workload is I/O-bound (parsing YAML, evaluating rules), not CPU-bound. Python is the right choice for the intelligence layer. A Go CLI wrapper or Operator can be added in later phases.

## Consequences

### Positive

1. **Eliminates duplication**: Shared infrastructure (CLI, MCP, eval, rendering) implemented once
2. **Accelerates new analyzers**: Adding a new migration domain requires only domain rules, not plumbing
3. **MCP-native from day one**: AI agents can immediately consume analysis tools
4. **CNCF-ready**: Apache 2.0, governance artifacts, clear positioning in an identified gap
5. **Community potential**: Each migration domain can attract its own contributor community

### Negative

1. **Abstraction overhead**: SDK abstractions may not perfectly fit every domain; some analyzers may need escape hatches
2. **Single-maintainer risk**: Currently only one maintainer; CNCF Sandbox requires diverse contributors
3. **Python in CNCF**: The Go-centric CNCF community may view Python unfavorably for core tooling
4. **Scope creep risk**: "Migration intelligence for everything" could become too broad

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Abstraction doesn't fit a domain | Analyzer ABC is minimal; domains can extend freely |
| No external contributors | Phase 2 focus: community building before CNCF submission |
| Python pushback | Phase 4: add Go CLI/Operator wrapper; core analysis stays Python |
| Scope too broad | Phase 1 ships with exactly one reference analyzer; expand only after validation |
| Konveyor overlap perception | Clear positioning: infrastructure API migration ≠ application modernization |

## Cross-Validation Results (2026-04-05)

Five parallel research tracks were conducted to stress-test this ADR:

### Track 1: Rule Engine Design
**Conclusion:** Custom Rule ABC is correct. Evaluated OPA/Rego, CEL (3 Python implementations), durable-rules, business-rules, rule-engine, GoRules Zen. None fit semantic analysis. CNCF tools (Pluto: hardcoded struct; kubent: embedded Rego; Kyverno: CRD+CEL; KubeLinter: YAML+Go template; Kubescape: Rego→CEL migration) all confirm the pattern of domain-specific rule implementations, not generic engines.

### Track 2: MCP Bridge Architecture
**Conclusion:** FastMCP 3.x (standalone, v3.1.1) offers advanced features (OpenAPIProvider, Transforms, component versioning) beyond the built-in SDK FastMCP. SSE is deprecated (removal 2026-06-30). A2A protocol (now under AAIF/Linux Foundation with MCP) is complementary, not competing — defer to Phase 3+. `.well-known/mcp/server.json` is the emerging discovery standard.

### Track 3: Competitive Landscape (adversarial)
**Conclusion:** Gap claim **substantiated with refinement**. Microsoft's Container-Migration-Solution-Accelerator is the closest threat (multi-agent + MCP) but is Azure-locked and monolithic. Konveyor KAI added Ingress→GW API migration (March 2026 blog) but targets source code, not YAML. Silver Surfer is in CNCF Sandbox but detection-only. No vendor-neutral pluggable SDK exists.

### Track 4: Python SDK Best Practices
**Conclusion:** hatchling + uv confirmed. Key updates: use minimum bounds (`>=`) not exact pins in pyproject.toml (SDK, not application); add Hypothesis for property-based testing of rule boundaries; add syrupy for pytest-native golden-file snapshots; use PEP 735 `[dependency-groups]` for dev deps. Target OpenSSF Scorecard 7+/10 from day one (CodeQL, Dependabot, branch protection).

### Track 5: CNCF Positioning
**Conclusion:** TAG Infrastructure (new since May 2025 restructuring) or TAG Developer Experience for positioning. CNCF "Cloud-Native Foundations for Distributed Agentic Systems" initiative (cncf/toc#1746) is directly relevant. Konveyor is complementary (app-layer), not competitive. CNCF Landscape category: "Provisioning > Automation & Configuration". Next TOC Sandbox review: 2026-06-09.

## Implementation Progress & Handoff Guide

> This section is a living record designed for cross-device/cross-session continuity.
> Any developer (including future-you on another machine) can read this section
> to understand exactly where the project stands and what to do next.

### Completed (Phase 1, Milestone 1 — 2026-04-05)

| Component | Files | Tests | Status |
|-----------|-------|-------|--------|
| Core Models (Finding, Report, Severity) | `src/shiftscope/core/models.py` | `tests/test_models.py` (14 tests) | DONE |
| Rule ABC (applies_to + evaluate) | `src/shiftscope/core/rule.py` | `tests/test_rule.py` (8 tests) | DONE |
| Analyzer ABC + Registry + run_rules() | `src/shiftscope/core/analyzer.py` | `tests/test_analyzer.py` (13 tests) | DONE |
| JSON Renderer | `src/shiftscope/render/json_renderer.py` | `tests/test_render.py` (6 tests) | DONE |
| Markdown Renderer | `src/shiftscope/render/markdown_renderer.py` | `tests/test_render.py` (5 tests) | DONE |
| Public API re-exports | `src/shiftscope/__init__.py` | — | DONE |
| Governance files | LICENSE, CONTRIBUTING, SECURITY, CoC, MAINTAINERS | — | DONE |
| ADR-001 (cross-validated) | `docs/adr/001-*.md` | — | DONE |
| pyproject.toml (hatchling + min bounds) | `pyproject.toml` | — | DONE |
| No-AI-coauthor guard | `.claude/settings.json`, `.git/hooks/commit-msg` | Verified | DONE |
| **Total: 193 tests passing (as of v0.2.0)** | | | |

### Remaining (Phase 1, Milestone 2)

| Task | Description | Key Design Decisions | Deps |
|------|-------------|---------------------|------|
| **Eval Harness** | Golden-file test runner: load case → run analyzer → diff against golden JSON | Use syrupy for pytest-native snapshots; support `--update-golden`; integrate with `EvalHarness` class | Models, Analyzer |
| **CLI Scaffolding** | Auto-generate Typer CLI from registered analyzers: `shiftscope analyze <analyzer> <input>` | Typer + Rich; subcommands per analyzer; `--output json|markdown`; graceful ImportError for optional `cli` extra | Analyzer, Registry |
| **MCP Bridge** | Auto-generate MCP tools from analyzers: `analyze_<name>`, `list_rules_<name>` | Use built-in FastMCP `@mcp.tool()` decorators; Pydantic models as params; stdio + Streamable HTTP transports; graceful ImportError for optional `mcp` extra | Analyzer, Registry |
| **Gateway API Analyzer** | Port from `gateway-migration-orchestrator/`: annotation rules, TLS risk rules, implementation profiles | YAML parser for Ingress resources; rules: cors, backend-protocol, auth-tls-secret, server-snippet, wildcard-tls; profiles: envoy-gateway, nginx-gw-fabric, cilium | All SDK core |

### Remaining (Phase 2+)

| Phase | Tasks | Target |
|-------|-------|--------|
| **Phase 2** | DRA analyzer (port from netintent-dra-bridge-v2); Helm 4 analyzer (port from helmforge-lab-m2); entry_points plugin discovery activation; README.md with quickstart | Community preview |
| **Phase 3** | Telco intent analyzer; agent readiness analyzer; optional PydanticAI augmentation; A2A Agent Card | Broader adoption |
| **Phase 4** | CNCF Landscape listing; TAG Infrastructure presentation; CNCF Sandbox proposal; CRD/Operator layer (Go wrapper) | CNCF submission (target: 2026-08 or 2026-10 TOC review) |
| **Phase 5** | GitHub Action; CI/CD integration; Argo Workflows; KubeCon NA 2026 CFP submission | Ecosystem integration |

### How to Continue Development on a New Device

```bash
# 1. Clone
git clone https://github.com/thc1006/shiftscope.git
cd shiftscope

# 2. Install Python 3.12+ (recommended: uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12

# 3. Bootstrap
make bootstrap
# OR manually: uv sync --group dev --group test --extra cli --extra mcp

# 4. Verify everything works
make verify
# Should see: 46 passed (or more if you've added tests)

# 5. Re-install commit-msg hook (not tracked by git clone)
cat > .git/hooks/commit-msg << 'HOOK'
#!/usr/bin/env bash
msg_file="$1"
if grep -Eiq 'Co-Authored-By:.*Claude|Generated with Claude Code' "$msg_file"; then
  echo "❌ Commit message contains AI attribution. Remove it and try again." >&2
  exit 1
fi
exit 0
HOOK
chmod +x .git/hooks/commit-msg

# 6. Continue from the next pending task
# See "Remaining (Phase 1, Milestone 2)" above
```

### Key Architectural Decisions to Preserve

These decisions were cross-validated through 5 research tracks and should NOT be changed without re-evaluation:

1. **Pydantic BaseModel** for Finding/Report (not dataclasses) — JSON Schema, validation, MCP integration
2. **ABC** for Rule/Analyzer (not Protocol) — explicit opt-in, runtime enforcement
3. **`applies_to()` + `evaluate()`** on Rule — Kyverno-inspired short-circuit pattern
4. **`run_rules()` helper** on Analyzer — eliminates duplicated loop in every analyzer
5. **`importlib.metadata.entry_points`** for plugin discovery — zero-dep, std lib
6. **Minimum bounds (`>=`)** in pyproject.toml — SDK, not application
7. **No Jinja2 core dep** — removed during code review; add back only when template customization needed
8. **No AI co-authorship** — `.claude/settings.json` + git hook; enforced by project policy
9. **Frozen models** — `ConfigDict(frozen=True)` on Finding/Report for immutability
10. **MCP transport**: Streamable HTTP (remote), stdio (local); SSE deprecated

### Source Projects (for porting analyzers)

These 6 prototype projects in the same parent directory contain domain logic to port:

| Analyzer to Build | Source Project | Key Source Files |
|-------------------|---------------|-----------------|
| Gateway API | `../gateway-migration-orchestrator/` | `src/*/rules.py`, `src/*/profiles.py`, `src/*/manifest_parser.py`, `configs/annotation_mappings.yaml` |
| DRA Networking | `../netintent-dra-bridge-v2/` | `src/*/compiler.py`, `src/*/templates.py`, `src/*/models.py`, `configs/example-intent.json` |
| Helm 4 Readiness | `../helmforge-lab-m2/helmforge-lab/` | `src/helmforge/analyzers.py`, `src/helmforge/oci_lab.py`, `configs/policy/` |
| Telco Intent | `../telco-intent-provenance-lab/*/` | `src/telco_intent_lab/compiler.py`, `src/*/provenance.py`, `src/*/adapters/` |
| Agent Readiness | `../agent-readiness-lab/*/` | `src/*/agents/orchestrator.py`, `src/*/schemas/readiness.py` |

## References

- [CNCF Sandbox Application Process](https://github.com/cncf/sandbox)
- [CNCF "Cloud-Native Foundations for Distributed Agentic Systems"](https://github.com/cncf/toc/issues/1746)
- [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Ingress NGINX Retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [ingress2gateway v1.0](https://kubernetes.io/blog/2026/03/20/ingress2gateway-1-0-release/)
- [Gateway API v1.5.0](https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.5.0)
- [DRA GA in K8s v1.34](https://kubernetes.io/blog/2025/09/01/kubernetes-v1-34-dra-updates/)
- [Helm 4 Released](https://helm.sh/blog/helm-4-released/)
- [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [Google: Migrating Code At Scale With LLMs (FSE 2025)](https://arxiv.org/abs/2504.09691)
- [CNCF Annual Report 2025](https://www.cncf.io/reports/cncf-annual-report-2025/)
- [Konveyor CNCF Page](https://www.cncf.io/projects/konveyor/)
- [kagent CNCF Page](https://www.cncf.io/projects/kagent/)
- [Microsoft Container-Migration-Solution-Accelerator](https://github.com/microsoft/Container-Migration-Solution-Accelerator)
- [Konveyor KAI — Ingress→GW API Blog (2026-03)](https://konveyor.io/blog/2026/migrating-ingress-nginx-go-to-gateway-api-konveyor-kai/)
- [Silver Surfer (Devtron) — CNCF Sandbox](https://github.com/devtron-labs/silver-surfer)
- [ing-switch](https://github.com/saiyam1814/ing-switch)
- [FastMCP 3.0 (standalone)](https://gofastmcp.com/updates)
- [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP Spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [AAIF (Agentic AI Foundation)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [A2A Protocol](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server)
- [Kubescape 4.0 — CEL Migration](https://www.cncf.io/blog/2026/03/26/announcing-kubescape-4-0-enterprise-stability-meets-the-ai-era/)
- [CEL-expr-python (Google)](https://opensource.googleblog.com/2026/03/announcing-cel-expr-python-the-common-expression-language-in-python-now-open-source.html)
- [APIMig (IJCAI 2025)](https://www.ijcai.org/proceedings/2025/829)
- [OpenSSF Scorecard](https://github.com/ossf/scorecard)
- [Python Packaging — Plugin Discovery](https://packaging.python.org/guides/creating-and-discovering-plugins/)
