---
type: platform-component
title: Harness Lifecycle Implications
description: downstream platform decisions pre-resolved by each harness choice
group: harness-selection
tags: [harness-selection, decision-routing, pre-resolved]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: mandate
decision-question: "Which downstream platform decisions are already resolved by the harness choice, and which remain open?"
decision-domain: harness_cascade
priority: 8
blocking: true
requires: [harness-selection/index]
---

Harness selection cascades into every other platform area. This node is the
routing map for the advisor: after harness selection, confirm pre-resolved
decisions fit the customer's constraints rather than re-designing them.

## Governed Multi-Harness Portfolio — partially pre-resolved

| Platform area | Pre-resolved by operating model |
|---|---|
| Governance shape | Shared control plane across approved harnesses |
| Identity baseline | SSO + population mapping must be common |
| Exception handling | Must exist explicitly; ad-hoc personal exceptions are not acceptable |
| Audit expectation | Cross-harness observability and spend attribution are mandatory |
| Tool posture | Every approved harness needs the same minimum governance checks |

**Remaining open:** which harnesses are in the approved portfolio, which
populations map to each harness, whether there is one default harness, and
whether an enterprise custom lane is needed for central execution or autonomy.

**Advisor action after multi-harness selection:** load
`harness-selection/multi-harness-governance`, then confirm the shared control
plane: identity, model policy, MCP/tool policy, audit, quota, and exception
workflow. Do not collapse the portfolio back into one product just to simplify
the architecture.

## SaaS Product — pre-resolved

| Platform area | Pre-resolved by vendor |
|---|---|
| Surfaces — IDE | Vendor's IDE extension; not customisable |
| Execution environment | Vendor-managed (local or cloud depending on product) |
| Agent Loop | Vendor-implemented; harness loop is not extensible |
| Permission Engine | Vendor admin console; limited per-organisation configuration |
| Identity (outbound credentials) | Vendor-brokered via SSO to your IdP |
| Quota / Spend limits | Vendor spend controls + your admin settings |
| Observability | Vendor dashboard + optional log export (product-dependent) |

**Advisor action after SaaS selection:** skip harness/runtime, harness/loop,
exec/* nodes. Confirm: does the pre-configured execution model, IDE surface,
and observability export meet the customer's compliance and governance requirements?
If any pre-resolved decision conflicts with a stated constraint, that is the
signal to reconsider the SaaS product choice.

## Managed Runtime (AgentCore) — pre-resolved

| Platform area | Pre-resolved |
|---|---|
| Execution isolation | microVM per session (AgentCore native) |
| MCP Gateway | AgentCore Gateway available (optional to adopt) |
| Identity (outbound) | AgentCore Identity workload identities |
| Observability backend | CloudWatch (review retention settings for compliance) |

**Remaining open:** surfaces, harness code design (agent loop, context, perms),
registry contents, model provider selection, quota/guardrails policy, model tiering.

## OSS Coding Harness — pre-resolved

| Platform area | Pre-resolved by harness |
|---|---|
| Agent loop | Harness-implemented; extensible within the harness's plugin/extension model |
| Core tool surface | Harness-defined (e.g., Pi: Read/Bash/Edit/Write; Cline: IDE tool set) |
| MCP integration | Varies by harness — Cline is native; OpenCode and Aider are not; verify per harness |
| Execution sandboxing | Varies — OpenCode/Cline/OpenHands have built-in isolation; Pi/Aider do not |
| Surface (IDE vs terminal vs platform) | Determined by harness design — Cline is IDE-native; Aider/Pi/OpenCode are terminal |

**Remaining open:** model provider selection, identity/access layer, quota/guardrails policy,
registry/MCP catalog, observability export, compliance overlay, cost attribution.

**Advisor action after OSS harness selection:** load `harness-selection/coding-harnesses`
and confirm the harness's pre-built execution and MCP posture fits the customer's
constraints. If the harness provides no built-in sandboxing (Pi, Aider), escalate to
`exec/container` or `exec/microvm` immediately — this is a required decision, not optional.
Then work remaining open nodes as normal.

## OSS Framework SDK — pre-resolved

Nothing is pre-resolved at the platform level. All node groups remain open
for explicit decision.

**Advisor action after OSS framework selection:** work through all mandate nodes in full,
then surface conditional nodes based on customer signals. This path produces
the most detailed architecture blueprint.

## Custom Build — pre-resolved

Nothing. All platform areas are fully open and all mandate nodes must be worked.
Rare: only justified when a core architectural requirement cannot be met by
any available framework primitive.

## Principles

- Surface the pre-resolved list to the customer immediately after harness selection —
  "Your choice pre-configures X, Y, Z — I'll confirm those defaults fit your
  constraints rather than redesigning them from scratch"
- Operating-model choices are as important as product choices — "governed
  portfolio" is a valid target-state answer, not a failure to decide
- Pre-resolved decisions are vendor commitments, not your own architecture —
  evaluate SLAs, feature availability, and enterprise-tier support before treating
  them as permanently fixed
- If any pre-resolved decision conflicts with a hard constraint (e.g., vendor
  observability export doesn't satisfy audit trail requirements), surface the
  conflict as a reason to reconsider harness choice before going deeper

## Connects to

All harness, exec, surfaces, and gateway nodes — this node is the skip-logic map
for the advisor conversation.
