---
type: platform-component
title: Tool Runtime
description: invokes tools · subagents
group: harness
tags: [harness, execution]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [custom-harness, managed-runtime, agentcore, oss-framework, build-vs-buy-harness]
decision-question: "Which harness runtime — SaaS product, managed runtime, or OSS framework — will orchestrate tool calls and model interactions?"
---

Executes the harness's decisions — runs built-in tools, loads skills,
spawns subagents, and dispatches MCP/model calls out through the gateways.
Never binds to a tool or model directly; every external call goes through
whichever gateway owns that category of call.

## Decisions

**Tool call routing?**
- All via gateways — one policy point for every external call, no
  exceptions
- Local tools direct, external via gateway — built-in local tools (file
  edit, local shell) execute in-process, while anything reaching outside
  the local environment routes through a gateway

**Subagent execution?**
- In-process — shared host with the parent, simpler but less isolated
- Isolated — separate context/sandbox per subagent, matching
  [Subagents](../registry/subagents.md)'s own principle that a subagent's
  scope should never exceed its parent's

**Call scheduling?**
- Parallelize read-only calls — independent reads have no ordering
  dependency and can run concurrently
- Serialize writes — writes to the same resource need ordering guarantees
  that parallel execution would violate

## Principles

- Bind to gateways, never directly to tools or models — this is what makes
  the [MCP Gateway](../gateway/mcpgw.md) and [Model Gateway](../gateway/modelgw.md)
  actual chokepoints rather than optional paths
- Parallelize read-only calls; serialize writes — a default scheduling
  policy, not a per-call judgment call each time
- A subagent's execution isolation should match its scope — an isolated
  subagent whose context still shares the parent's credentials isn't
  actually isolated

## Connects to

- Routes every tool call through the [MCP Gateway](../gateway/mcpgw.md);
  never a direct connection from the runtime to a backend
- Dispatched by the [Agent Loop](loop.md) on each cycle
- Executes subagents per [Subagents](../registry/subagents.md)'s
  delegation policy and depth/fan-out caps
- Runs within whichever [sandboxing component](../exec/index.md) the
  platform has chosen

## Sources

- Verify against current docs — this file describes the general
  tool-runtime pattern (gateway-bound dispatch, parallel-reads/serial-writes
  scheduling) as stated in the original architecture diagram, not a
  citation-backed claim about one specific product's runtime
  implementation. Corroborate with a concrete source before treating any
  claim here as settled fact.
