# ShiftScope

**Migration intelligence for cloud-native infrastructure.**

ShiftScope is a pluggable framework for building migration intelligence analyzers for Kubernetes infrastructure API transitions. Deterministic-first risk analysis with MCP-native exposure for AI agent consumption.

## Status

Alpha (v0.1.0) — core SDK implemented, reference analyzers in progress.

## Quick Start

```bash
# Install (requires Python 3.12+)
pip install shiftscope[cli]

# List available analyzers
shiftscope list

# Run an analyzer
shiftscope analyze gateway-api path/to/ingress.yaml --output markdown
```

## Architecture

See [ADR-001](docs/adr/001-unified-migration-intelligence-sdk.md) for the full architectural decision record including cross-validation results.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
