# KubeCon NA 2026 CFP Draft

## Title
Surviving the Next Kubernetes API Deprecation Wave: What ingress2gateway Won't Tell You

## Abstract (200 words)

Ingress NGINX retired on March 24, 2026, affecting 50% of Kubernetes clusters. Tools like ingress2gateway handle YAML conversion, but five subtle behavioral differences between ingress-nginx and Gateway API cause silent 404s that no conversion tool detects: regex matching semantics, cross-Ingress annotation leakage, implicit regex activation via rewrite-target, missing trailing-slash redirects, and URL normalization variance.

We built ShiftScope, an open-source migration intelligence SDK that detects these behavioral risks before they become production incidents. In this talk, we'll share:

1. Real-world migration war stories: 120 engineer-hours across 47 clusters, and what broke that nobody expected
2. The 5 behavioral differences demonstrated with live YAML examples
3. How ShiftScope's cross-Ingress analysis detects risks that per-resource tools miss
4. Beyond Gateway API: applying the same pattern to DRA networking migration, MCP server security (82% have path traversal vulnerabilities), and AI agent governance
5. Ship it everywhere: GitHub Action with SARIF Code Scanning, Helm chart for cluster-native scanning, MCP server for AI agent consumption

Attendees will leave with a concrete checklist for their own migrations and a pluggable SDK they can extend for their infrastructure's specific deprecation challenges.

## Talk Format
Breakout Session (25 min) or Lightning Talk (5 min)

## Target Audience
Platform engineers, SRE, DevOps engineers managing Kubernetes infrastructure migrations

## Benefits to Ecosystem
Fills the gap between API version detection (Pluto/kubent) and format conversion (ingress2gateway) with behavioral risk analysis — a pattern applicable to every K8s API deprecation cycle.
