---
type: platform-component
title: Subagents
description: delegated specialists
group: registry
tags: [registry, subagents, delegation]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Purpose-built agents the main harness can spawn for scoped work (explore,
review, migrate) — each running in its own context window with its own
system prompt, tool access, and permissions, rather than sharing the parent
conversation's context. The main reasons to delegate: keeping large
exploratory output (search results, logs) out of the main conversation, and
routing narrow tasks to a cheaper/faster model.

## Decisions

**Delegation policy?**
- Fixed roster — only approved subagent definitions may be spawned, nothing
  ad hoc
- Depth / fan-out caps — stop runaway trees; concretely, a depth limit
  controls how many layers of subagents-spawning-subagents are allowed
  (setting it to a low value effectively disables nested spawning), and a
  separate limit controls how many subagents may run concurrently at any
  one time — these are two independent caps, not one setting
- Budget caps per subagent — route cost-sensitive delegated work to a
  cheaper/faster model rather than inheriting the parent's model by default

**Tool access relative to the parent?**
- Full inheritance — subagent gets whatever the parent has; simplest,
  least safe
- Explicit allowlist per subagent — a subagent's tool list is defined on
  the subagent itself, independent of the parent's grants
- Read-only by construction — omit write-capable tools entirely from a
  subagent meant to only review/explore, so it cannot exceed that role even
  if instructed to

## Principles

- Subagent scope should never exceed the parent's — a subagent is for
  narrowing scope, not for a workaround to grant broader access than the
  parent has
- Nesting depth and concurrent-spawn count are separately capped — a depth
  limit alone doesn't bound how many subagents run at once, and a
  concurrency limit alone doesn't bound how deep a delegation chain goes;
  both matter for stopping a runaway tree
- A reviewing/read-only subagent should have write-capable tools omitted
  entirely from its definition, not merely instructed not to use them —
  an instruction is not an access control

## Connects to

- Defined in and loaded from the [Registry / Catalog](registry.md)
- Delegation depth/fan-out policy should be reconciled with whatever
  autonomy level is set in the [Agent Loop](../harness/loop.md) — a
  fully autonomous parent spawning uncapped subagents compounds risk rather
  than bounding it

## Sources

- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) — checked 2026-08-12 — supports: subagents running in their own context window with independent system prompt/tool access/permissions, cost control by routing to a cheaper model, an explicit nesting-depth limit (configurable, defaults to disabled/single-layer unless raised) separate from a concurrent-spawn limit, tool-access restriction via omitting a tool from the subagent's allowed list rather than instructing it not to use that tool
