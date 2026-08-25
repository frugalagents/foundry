---
type: platform-component
title: Model Tiering
description: route tasks to the right model tier — capability-cost matching
group: gateway
tags: [gateway, model-routing, cost-optimization, model-tiering, task-complexity]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [model-tiering, cost-optimization, cheaper-model, task-complexity-routing, tiered-model-strategy]
decision-question: "How will you match task complexity to model capability so that simple tasks use cheaper models and frontier models are reserved for tasks that need them?"
decision-domain: model_routing
priority: 7
requires: [gateway/modelgw]
---

Model tiering is the practice of routing tasks to the cheapest model that can
handle them well — sending autocomplete and simple queries to Haiku-class models,
single-file edits to Sonnet-class, and multi-file reasoning to frontier Opus-class.
Without tiering, all requests consume frontier tokens regardless of need.

## Tier Reference

| Tier | Model class | Typical tasks | Relative cost |
|---|---|---|---|
| T1 — Fast | Haiku-class (claude-haiku-4-5) | Autocomplete, inline suggestion, simple Q&A, short test gen | ~1x |
| T2 — Mid | Sonnet-class (claude-sonnet-4-6) | Single-file edits, code review, moderate reasoning, short summaries | ~5x |
| T3 — Frontier | Opus-class (claude-opus-4-6) | Multi-file refactors, architecture reasoning, long-context analysis, complex debugging | ~15x |

Note: relative costs change; always check current pricing before asserting specific
numbers. See sources.

## Decisions

**How is task complexity assessed?**
- Heuristic signals — token count of the request, number of files referenced,
  presence of routing keywords ("refactor all", "across the codebase", "architecture"):
  low overhead, good enough for most cases
- Model self-classification — a cheap model classifies the task, then the gateway
  routes accordingly; adds one round-trip latency and a small classification cost;
  justified only if heuristics misfire frequently
- Explicit developer selection — IDE plugin lets the developer choose tier;
  gives control; removes automation benefit; useful as an escape hatch, not a primary mechanism

**Where does routing logic live?**
- [Model Gateway](modelgw.md) — clean separation; the harness sends an unqualified
  model ID or a complexity hint; the gateway selects the target; recommended
- Inside the harness — more coupling; duplicates routing logic that the gateway
  already handles

**What is the escalation policy?**
- Task fails at T1 → auto-escalate to T2; fail at T2 → auto-escalate to T3:
  resilient but can mask poor routing calibration
- Hard routing with no auto-escalation: simpler, predictable cost, requires
  accurate initial routing
- Developer-override allowed: developer can force-escalate; tracked for cost
  attribution; useful escape hatch

**What are the tier boundaries?**
- Default heuristic: single-file scope → T2; multi-file or cross-repo scope → T3;
  inline/short → T1
- Calibrate against your eval harness — if T2 is failing tasks you've assigned
  it, the boundary needs adjustment, not a blanket upgrade to T3

## Stack Options

**Routing (AWS managed)**
- Amazon Bedrock cross-region inference profiles — configure a profile that
  spans multiple regions for the same model family; Bedrock routes to available
  capacity automatically; primary mechanism for both tiering and resilience in
  a Bedrock-native stack; set a profile per tier (T2 profile, T3 profile)
- AgentCore Model Gateway — configure targets per model tier; routing rules
  map model IDs to targets; exact match over glob; supports qualified model IDs
  (`{target}/{model}`) for pinning a request to a specific provider

**Routing (open source)**
- LiteLLM proxy — self-hosted; configure named deployments per tier; supports
  cost-based routing (picks cheapest model satisfying the call), usage-based
  routing (avoids saturated deployments via live Redis tracking), and latency-
  based routing; deployment cooldown after failures; priority-ordered tiers
  with same-tier weighted failover; the most feature-complete OS option
- OpenAI-compatible proxy (custom) — simple reverse proxy that rewrites the
  `model` field based on a complexity signal in a request header; low overhead,
  limited intelligence; suitable if routing logic is simple heuristics

**Complexity classification**
- Heuristic in harness code — compute token count + file-reference count +
  keyword scan on the request; annotate request with a `X-Complexity-Tier`
  header; gateway reads this header for routing; no extra model call
- Bedrock Haiku classification step — cheapest Bedrock call to classify
  complexity; latency impact ~200ms; justified only if heuristics misfire
  at a rate that materially affects cost or quality

**Tier boundary calibration**
- Amazon CloudWatch + custom dashboard — track per-tier success rate, retry
  rate, and developer override frequency; use this data to recalibrate
  complexity thresholds quarterly
- Bedrock model evaluation — run your eval suite against T2 and T3 models
  for your specific task distribution; boundary is right when T2 passes
  tasks you've classified as mid-complexity at > your quality threshold

## Principles

- Tiering is a cost control, not a quality degradation — the principle is that
  complex tasks always reach the right model, not that you cheap out on reasoning
- Haiku-class is fast enough for latency-sensitive surfaces (autocomplete, inline
  suggestions); use it there unconditionally regardless of "quality" concerns —
  latency sensitivity beats quality ceiling for that use case
- Never make T3 inaccessible to a developer who judges their task needs it —
  tiering is a default routing policy, not a hard ceiling; gate with approval
  and cost attribution, not with blocking
- Track per-tier task-success rate in your eval harness; if T2 failure rate on
  "mid-complexity" tasks exceeds a threshold, recalibrate the boundary before
  blaming the model

## Connects to

- [Model Gateway](modelgw.md) — the enforcement point; model tiering defines
  the policy, the gateway executes it
- [Model Providers](../external/providers.md) — each tier maps to a provider
  endpoint; tiers and providers are distinct concerns
- [Token Economics](../ops/token.md) — tiering is the primary lever for reducing
  per-call token cost; cache stability per tier is also a design consideration
- [Cost Management](../ops/cost.md) — aggregate cost by tier in reporting to
  validate whether the routing policy achieves its cost targets
- [Agent Evals](../quality/evals.md) — per-tier quality tracking is the feedback
  loop that keeps tier boundaries calibrated

## Sources

- [Anthropic model pricing](https://www.anthropic.com/pricing) — must re-check on schedule; never assert specific price without a checked date
- [LiteLLM Routing](https://docs.litellm.ai/docs/routing) — checked 2026-08-13 — cost-based routing strategy selects cheapest model satisfying the call; usage-based and latency-based strategies also available
