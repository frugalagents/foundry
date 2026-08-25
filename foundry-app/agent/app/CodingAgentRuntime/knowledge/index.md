---
type: platform-component-group
title: Coding Agent Platform Designer — Knowledge Base
description: OKF bundle of platform components for designing a coding agent platform
group: root
tags: [okf, root]
timestamp: 2026-08-12T00:00:00Z
status: candidate
decision-domain: root_scope
priority: 1
---

Open Knowledge Format bundle backing the coding agent platform designer chat
tool. 68 components across 11 groups — see `ARCHITECTURE.md` §2 for the full
taxonomy and rationale, `IMPLEMENTATION_PLAN.md` for build status.

Built up in phases per `IMPLEMENTATION_PLAN.md`: a 5-component thin slice
(Phase 1) proved the OKF schema and cross-linking convention; Phase 4 built
out the remaining 27 components batch-by-group. All 32 original components
written; Phase 5 added 2 new groups and 7 new nodes (39 total); Phase 6 added
18 more nodes surfaced from enterprise simulation scenarios and regulatory
expansion (57 total); Phase 7 added 5 high-priority nodes from cross-simulation
gap analysis (62 total): vault-integration, jupyterlab, model-risk-management,
mnpi, safety-critical-eval; Phase 8 added 4 medium-priority nodes (66 total):
gcp-runner, cyberark-integration, sox, cost-model-enterprise; Phase 9 added 1
node (67 total): coding-harnesses (distinguishes pre-built OSS coding harnesses
from framework SDKs; covers OpenCode, Pi, Cline, Codex CLI, OpenHands, Goose,
Aider, Mastra, SWE-agent, Deep Agents). Phase 10 adds 1 node (68 total):
multi-harness-governance, covering approved tool portfolios, default-plus-
exceptions models, and shared governance across multiple coding harnesses.

All nodes tagged with `traversal` (mandate / conditional / probe),
`trigger` signals, and `decision-question` fields.

## Groups

- [Surfaces](surfaces/index.md) — 5/5 (added: jupyterlab)
- [Access](access/index.md) — 16/16 (added: security-posture, policy-tiers, progressive-trust, security-ops, export-control, legal-hold, idp-federation, regional-compliance, data-jurisdiction, hipaa, cmmc, model-risk-management, mnpi, sox)
- [Registry](registry/index.md) — 6/6
- [Harness](harness/index.md) — 6/6
- [Harness Selection](harness-selection/index.md) — 6/6 (new group: saas-products, multi-harness-governance, managed-runtime, oss-frameworks, lifecycle-implications; added: coding-harnesses)
- [Execution](exec/index.md) — 6/6 (added: on-prem-runner, gcp-runner)
- [Gateway](gateway/index.md) — 5/5 (added: model-tiering, vault-integration, cyberark-integration)
- [External](external/index.md) — 3/3
- [Knowledge Layer](knowledge-layer/index.md) — 3/3 (new group: code-intelligence, org-knowledge, standards-injection)
- [Ops](ops/index.md) — 8/8 (added: session-economics, resilience, multi-cloud-governance, federation, cost-model-enterprise)
- [Quality](quality/index.md) — 3/3 (added: model-capability-eval, safety-critical-eval)

## Traversal Summary

- **Mandate** (always traversed): ide, identity, guardrails, quota, providers,
  observability, exec/local, security-posture, harness-selection/index,
  harness-selection/lifecycle-implications, harness-selection/saas-products
- **Conditional** (signal-triggered): cli, chat, ci, registry, tools, mcpservers,
  mcpgw, modelgw, model-tiering, runtime, loop, memory, container, microvm, remote,
  landscape, cost, evals, session-economics, policy-tiers, knowledge-layer/*,
  managed-runtime, coding-harnesses, oss-frameworks, export-control, legal-hold, multi-cloud-governance,
  idp-federation, regional-compliance, data-jurisdiction, ops/federation,
  model-capability-eval, on-prem-runner, hipaa, cmmc, vault-integration,
  jupyterlab, model-risk-management, mnpi, safety-critical-eval, gcp-runner,
  cyberark-integration, sox, cost-model-enterprise
- **Probe** (explicit customer request only): context, perms, rollback, provenance,
  skills, subagents, web, token, progressive-trust
