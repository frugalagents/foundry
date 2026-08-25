---
type: platform-component-group
title: Harness Selection
description: single harness, governed portfolio, or custom build — picking the agent orchestration layer
group: harness-selection
tags: [harness-selection, governance, build-vs-buy]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: mandate
decision-question: "What is the target-state operating model for harnesses: one standard tool, a governed portfolio, or a custom-built path?"
decision-domain: operating_model
priority: 10
blocking: true
implies: [harness-selection/lifecycle-implications, harness-selection/saas-products, harness-selection/managed-runtime, harness-selection/coding-harnesses, harness-selection/oss-frameworks]
---

The harness is the orchestration layer that drives the agent loop, dispatches
tool calls, and manages model interactions. Picking the harness operating model
is the earliest decision with the most downstream consequences — it pre-resolves
surface, execution, and often identity choices before you ever design them
explicitly.

In brownfield enterprises, the first decision is often not which product wins.
It is whether the target state should be:

- one standard harness
- a governed multi-harness portfolio
- one default harness with formal exception paths

Resolve that operating model before narrowing to specific products or custom
build paths.

## A Note on Terminology

Two different things are often called "harness" — they are not the same:

**Pre-built coding harnesses** (OpenCode, Pi, Cline, Codex CLI) ship all four layers already connected — Core (model + loop), Execution (tools, sandbox, file/git ops), Intelligence (memory, context engineering, MCP), Governance (guardrails, observability). You configure and deploy.

**Framework SDKs** (Strands, LangChain, PydanticAI, AutoGen) give you primitives you assemble into an agent loop. You own the wiring, the ops lifecycle, and every design decision.

The practical difference matters: same model, different harness → 20-point swing in benchmark pass rates (68–88% in a 2026 empirical study). Harness architecture drives outcomes independently of model selection.

## Sub-nodes

- [SaaS Products](saas-products.md) — Claude Code, Cursor Enterprise, GitHub Copilot, Kiro
- [Multi-Harness Governance](multi-harness-governance.md) — approved portfolio, default + exceptions, shared controls
- [Managed Runtime](managed-runtime.md) — Bedrock AgentCore: compliance-grade cloud runtime, custom code, managed infra
- [OSS Coding Harnesses](coding-harnesses.md) — OpenCode, Pi, Cline, Codex CLI, Goose, Aider, OpenHands, Mastra, SWE-agent, Hermes
- [OSS Framework SDKs](oss-frameworks.md) — Strands, LangChain/LangGraph, PydanticAI, AutoGen, CrewAI — build your own harness
- [Lifecycle Implications](lifecycle-implications.md) — what each choice pre-resolves downstream

## Decision Spectrum

| Option | Control | Setup cost | Ops burden | Extensibility |
|---|---|---|---|---|
| SaaS product | Low | Near-zero | None | Vendor-limited |
| Managed runtime (AgentCore) | Medium | Days–weeks | Low | High (custom code, managed infra) |
| OSS coding harness | Medium–High | Days | Low–Medium | Harness-limited then full |
| OSS framework SDK | High | Weeks | Medium | Full |
| Custom build | Full | Months | High | Full |

Choose the leftmost option that satisfies your constraints — control is expensive.
