---
type: platform-component
title: Quota & Rate Limits
description: throttling · seats · spend caps
group: access
tags: [access, governance, cost-control]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: mandate
decision-question: "How will you cap, throttle, and attribute spend per developer and team — and what happens when limits are breached?"
decision-domain: cost_control
priority: 8
blocking: true
requires: [access/identity]
implies: [ops/cost]
---

Enforces limits at the edge before any model or tool spend — per-caller,
per-tool, or per-target throughput limits, concurrency caps, and hard spend
ceilings. Concretely, this works by grouping traffic into buckets along
dimensions (e.g. caller identity, tool, target) and setting an allowed rate
per bucket; every applicable limit must pass for a request to proceed.

## Decisions

**Limit model?**
- Per-user + per-team rate limits — grouped by caller identity (JWT claims
  or IAM identity)
- Concurrency caps — bound parallel agent sessions/connections rather than
  request rate
- Hard spend ceiling per team — a dollar cap rather than a throughput cap
- Per-tool / per-target throughput — protects a specific backend from a
  traffic spike regardless of who's calling it, useful when one tool is a
  shared bottleneck across many callers

**What happens when a limit is hit?**
- Block the request (rate value of zero for a specific caller blocks them
  entirely — useful for cutting off a specific bad actor without touching
  everyone else's limits)
- Queue/backoff — hold the request rather than reject it outright
- Alert-only at a threshold, hard cap only at 100% — gives visibility before
  the cap actually bites

## Principles

- Enforce quotas before spend, at the edge — this component sits ahead of
  the model/tool call, not as a post-hoc bill audit
- Alert at 80%, cap at 100% — visibility before the hard stop, not just the
  hard stop itself
- All configured limits must pass (AND logic) — a request can be blocked by
  any one dimension's limit even if every other dimension has headroom
- **Rate limits commonly fail open by default**: if the limiting service
  itself is unavailable or a dimension can't be resolved, the request is
  allowed to proceed rather than blocked. Don't rely on rate limiting alone
  as a security boundary — pair it with [Guardrails & Policy](guardrails.md)
  for anything that's actually a security control, not just a cost control
- Customer-defined limits can't exceed a service-managed ceiling — the
  effective limit is always the minimum of what you configure and what the
  underlying platform enforces

## Connects to

- Complements, but is not a substitute for, [Guardrails & Policy](guardrails.md)
  for security-relevant enforcement — see the fail-open principle above
- Enforced alongside the same [Identity & Access](identity.md) model, since
  per-user/per-team limits are keyed off the same caller identity

## Sources

- [Add rate limits to a gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-rate-limits.md) — checked 2026-08-12 — supports: dimension-key-based traffic grouping with per-bucket rate entries, AND logic across multiple active rate limits, a rate value of zero as an explicit block for a specific caller, customer-defined limits capped by a service-managed ceiling, and the fail-open default behavior when the rate-limiting service is unavailable or a dimension can't be resolved
