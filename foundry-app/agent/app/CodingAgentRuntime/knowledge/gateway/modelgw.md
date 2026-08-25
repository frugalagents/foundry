---
type: platform-component
title: Model Gateway
description: broker to model providers
group: gateway
tags: [gateway, governance, model-routing]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [multi-provider, model-routing, cost-optimization, provider-fallback, tiered-model-strategy]
decision-question: "Do you need to route model calls across providers or tiers for cost, resilience, or compliance?"
decision-domain: model_routing
priority: 8
implies: [gateway/model-tiering, access/quota]
---

The chokepoint for all LLM calls to model providers — routes by task
complexity or explicit request, applies fallback and rate limits, and
meters tokens for cost attribution. Concretely, a model gateway can present
multiple providers (Bedrock, OpenAI, Anthropic direct) behind a single
inference endpoint, matching each request's `model` field to a configured
target rather than the harness holding separate credentials and clients
per provider.

## Decisions

**Model strategy?**
- Frontier-only — simplest, best raw quality, most expensive per call
- Tiered routing — route by task complexity to a cheaper model for simple
  steps; requires the gateway to support multiple targets/models behind one
  endpoint
- Self-hosted / BYO — needed for residency or air-gapped requirements a
  managed provider can't satisfy

**Provider posture?**
- Single provider — simpler operationally, no fallback if that provider has
  an outage
- Multi-provider with fallback — more resilient; requires the gateway to
  support routing to more than one provider and a policy for what happens
  when multiple configured targets could serve the same model

**How is a specific model/provider selected per request?**
- Unqualified model ID — the gateway matches it against all configured
  targets; an exact match wins over a glob pattern, and if exactly one
  target matches, it's used
- Qualified model ID (`{target}/{model}`) — pins the request to a specific
  provider explicitly, bypassing the gateway's own matching logic entirely

**When multiple targets can serve the same model, what routing strategy picks among them?**
- Simple/random shuffle — lowest latency overhead, a reasonable default
  when deployments are roughly interchangeable
- Usage-based (lowest current token/request usage, tracked live e.g. via
  Redis) — filters out already-saturated deployments before picking
- Latency-based (lowest observed response time) — needs a buffer/ramp
  mechanism so a newly-fast-looking deployment doesn't get flooded
  immediately
- Cost-based (lowest price for the call) — needs a maintained provider
  pricing table to evaluate against
- Least-busy (fewest concurrent in-flight calls) — simplest usage-aware
  strategy, no historical tracking required
- Fixed precedence with round-robin fallback — default to one specific
  provider when it's among the matches, otherwise distribute across matches

## Principles

- Route by complexity to control cost — this is the tiered-routing
  decision's whole point, not just an efficiency nice-to-have
- Prompt-cache stable context — ties directly into
  [Token Economics](../ops/token.md)
- Meter tokens here for attribution — the gateway is the natural single
  point to attribute spend, since every model call passes through it
  regardless of which provider served it
- Credential material for outbound provider calls is injected by the
  gateway from a stored credential, never passed as a raw parameter — same
  posture as the [MCP Gateway](mcpgw.md)'s outbound credential handling
- When multiple providers can serve the same model, routing collisions need
  an explicit resolution policy from the strategies above — silently
  picking one non-deterministically makes cost and latency behavior
  unpredictable
- A failing deployment should cool down (be temporarily removed from the
  pool after exceeding an allowed-failure threshold within a time window)
  rather than being retried immediately on every subsequent request —
  prevents a single bad deployment from repeatedly absorbing traffic and
  failing again
- Deployment priority ordering (try tier 1, fall back to tier 2, etc.) and
  same-tier weighted failover are two distinct fallback mechanisms — decide
  whether failover happens within a priority tier before ever escalating to
  the next tier, or escalates immediately

## Connects to

- Routes calls to [Model Providers](../external/providers.md) — the actual
  inference destinations behind this gateway's targets
- Same credential-brokering posture as the [MCP Gateway](mcpgw.md) — both
  gateways inject credentials server-side rather than accepting them as
  call parameters
- Feeds [Token Economics](../ops/token.md) and [Cost Management](../ops/cost.md)
  with per-call metering data
- Reached by the [Tool Runtime](../harness/runtime.md) for every model
  call, same "bind to gateways, never directly to models" principle as tool
  calls

## Sources

- [Inference provider targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-inference-provider.md) — checked 2026-08-12 — supports: multiple model providers configured as targets behind one inference endpoint, model-based routing with exact-match-over-glob-pattern precedence and explicit collision handling (defaulting to a specific provider when present among matches, otherwise round-robin), qualified model IDs (`{target}/{model}`) to pin a request to a specific provider explicitly, and provider credential injection via IAM or a stored API key rather than passing credentials as call parameters
- [LiteLLM — Routing](https://docs.litellm.ai/docs/routing) — checked 2026-08-13 — supports (as of 2026-08-13): distinct named routing strategies (simple-shuffle default, usage-based via live Redis-tracked TPM/RPM, latency-based with a ramp buffer, cost-based via a pricing table, least-busy by concurrent call count), deployment cooldown after an allowed-failure threshold within a time window, and priority-ordered deployment tiers with same-tier weighted failover before cross-tier escalation
