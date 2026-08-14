---
type: platform-component
title: Token Economics
description: metering · cache · right-sizing
group: ops
tags: [ops, cost, tokens]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

The efficiency layer — token metering, prompt-cache hit rate, model
right-sizing, and cost-per-task optimization. Distinct from
[Cost Management](cost.md)'s attribution/chargeback concern: this component
is about *reducing* the token bill in the first place, not about who gets
billed for what remains after optimization.

## Decisions

**Optimization levers?**
- Tiered model routing — a cheaper/faster model for simple steps (e.g.
  subagent tasks), reserving the most capable model for complex
  architectural or multi-step reasoning
- Prompt caching — reuse stable context (system prompt, CLAUDE.md-style
  rules) across calls rather than reprocessing it every time; cache hit
  rate is highly sensitive to session gaps, since a break longer than the
  cache's lifetime causes a full-price cache miss on the next call
- Context compaction — proactively summarize/trim conversation history
  before it grows large, rather than only reactively compacting once a
  limit is hit
- Delegate high-volume operations (test runs, log processing, doc fetches)
  to a subagent so the verbose output stays in the subagent's own context
  and only a summary returns to the main conversation

**What do you optimize for?**
- Cost per successful task — the metric that actually matters; raw token
  count alone doesn't distinguish an efficient success from a cheap
  failure
- Latency — a different, sometimes competing objective; the cheapest model
  isn't always the fastest for a given task
- Balanced — most deployments land here in practice, trading a bit of each
  against the other rather than maximizing either alone

**How aggressively to manage context?**
- Reactive only — compact/clear only once a limit is actually hit; simplest,
  but a long-running session can silently accumulate a large fraction of
  its total cost just from re-sending stale history on every turn
- Proactive — clear between unrelated tasks, move rarely-needed reference
  material out of always-loaded context (e.g. into on-demand-loaded
  skills rather than an always-loaded rules file) before hitting a limit

## Principles

- Track cost-per-task, not just raw tokens — a task that used more tokens
  but succeeded on the first attempt can be cheaper overall than one that
  used fewer tokens per turn but needed several retries
- Maximize prompt-cache hit rate deliberately — cache misses are a real,
  identifiable cost driver (session gaps beyond the cache lifetime, a
  changed system prompt), not just background noise
- Right-size the model to the step — routing every step to the most capable
  model by default is a choice, and usually not the cheapest one
- A long-idle session can carry a full day's context on every subsequent
  message — this is often the actual answer to "why did a single short
  question cost so much," not a mystery
- Preprocessing verbose output before it reaches the model (filtering a log
  to just the error lines, for instance) is often more effective than
  trying to get the model to be economical with an unfiltered firehose of
  text

## Connects to

- Feeds the same underlying telemetry as [Cost Management](cost.md) and
  [Observability & Audit](observability.md), viewed through an
  optimization lens rather than an attribution or debugging lens
- Ties directly into [Model Gateway](../gateway/modelgw.md)'s
  tiered-routing decision and [Context](../harness/context.md)'s
  compaction-strategy decision — this component is where those two
  decisions' cost impact is actually measured

## Sources

- [Manage costs effectively](https://code.claude.com/docs/en/costs) — checked 2026-08-12 — supports: model right-sizing (cheaper models for subagent/simple tasks, reserving the most capable model for complex reasoning), prompt-cache hit-rate sensitivity to session gaps beyond the cache lifetime causing full-price cache misses, delegating high-volume/verbose operations to subagents to keep verbose output out of the main context, proactive context management (clearing between tasks, moving reference material into on-demand-loaded skills) as a real cost lever distinct from reactive-only compaction, and the specific finding that a long-idle session resending full history is a common, identifiable driver of otherwise-surprising per-message cost
