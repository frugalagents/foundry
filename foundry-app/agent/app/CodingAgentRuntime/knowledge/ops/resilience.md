---
type: platform-component
title: Resilience & Scaling
description: HA posture, provider fallback, circuit-breakers, graceful degradation
group: ops
tags: [ops, resilience, ha, scaling, circuit-breaker, fallback]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [high-availability, scaling, multi-region, provider-fallback, resilience, production-traffic]
decision-question: "How will your platform handle provider outages, harness failures, and traffic spikes without a full developer productivity outage?"
---

A coding agent platform is infrastructure — when it goes down, developers lose
their primary productivity tool. Resilience design answers what happens when a
component fails, not just how the happy path works.

## Failure Surface

| Component | Failure mode | Developer impact |
|---|---|---|
| Model provider | Outage or rate-limit throttling | All model calls fail or queue; agent sessions stall |
| Harness runtime | Process crash or overload | Active sessions dropped; queued sessions blocked |
| MCP gateway | Unavailable | Tool calls fail; agent cannot reach enterprise systems |
| MCP server (specific) | Unavailable | That system's tools fail; others unaffected if isolated |
| Execution sandbox | Container/VM launch failure | Task execution fails; agent cannot run code |
| Network path (VPC/private) | Connectivity drop | Inference and tool calls fail simultaneously if single path |

## Decisions

**Model provider resilience?**
- Single provider, no fallback — simplest; a provider outage = platform outage
- Single provider with retry and exponential backoff — handles transient errors and
  rate-limit bursts; does not survive a sustained outage
- Multi-provider fallback — primary provider unavailable → route to secondary;
  requires [Model Gateway](../gateway/modelgw.md) to support multi-target routing;
  see `modelgw.md` for routing strategy options
- Recommended: single-provider with retry for phase one; add multi-provider fallback
  once traffic data justifies the operational complexity

**Harness HA posture?**
- Single instance — acceptable for a pilot; not for production; single point of
  failure for all developer sessions
- Active-active with load balancer — multiple harness instances behind a load
  balancer; session affinity if stateful session data is in-process
- Managed runtime (AgentCore) handles HA natively — no customer HA design needed;
  verify SLA meets your requirement

**Circuit-breaker for failing dependencies?**
- No circuit-breaker — every request retried to a failing dependency; amplifies
  load on an already-degraded system
- Circuit-breaker per dependency — after N consecutive failures within a time
  window, open the circuit; return a degraded response rather than retrying;
  close after a probe succeeds; see `modelgw.md` for deployment cooldown pattern
  (same principle applied at the gateway level)
- Recommended: circuit-breaker on model provider calls and MCP gateway calls;
  fail-fast with a meaningful user error ("GitHub integration temporarily
  unavailable") beats a 30-second timeout

**Graceful degradation posture?**
- Model provider down → surface an error and ask developer to retry; acceptable
- Model provider down + fallback provider → transparent to developer; preferred
- MCP server down → agent notifies developer of limited tool access, continues
  with remaining tools; do not fail the entire session because one integration
  is unavailable
- Harness overloaded → queue with position visibility, not silent drop

**Multi-region?**
- Single region — acceptable for most deployments; adds a region-specific outage
  risk but removes operational complexity
- Active-passive multi-region — primary region handles all traffic; secondary
  warm-standby for DR; manual or automated failover
- Active-active multi-region — traffic split geographically; complex session
  state synchronization required; justified only for large platforms where
  regional latency is a material developer productivity factor

## Principles

- Design for partial failure, not just total availability — a platform that
  degrades gracefully under one component failure is more resilient than one
  that either works perfectly or collapses entirely
- Fail fast, not slow — a 30-second timeout feels worse than an immediate error;
  set aggressive timeouts at every dependency boundary
- Retry budgets matter — unbounded retries amplify load on a degraded provider;
  always pair retries with exponential backoff and a maximum retry count
- Measure recovery time, not just uptime — MTTR (mean time to recovery) is the
  operational metric that matters to developers; uptime % is less actionable

## Stack Options

**Retry + backoff (all harness types)**
- AWS SDK (Boto3, SDK for Java/Node) — built-in retry config with exponential
  backoff and jitter; set `max_attempts` and `retry_mode = adaptive` per service
  client; no extra infrastructure
- LiteLLM — `num_retries` and `retry_after` config per model deployment; works
  across providers

**Circuit-breaker**
- AWS SDK adaptive retry mode — circuit-breaker behaviour built in; opens on
  sustained errors to prevent request storms against a degraded provider
- Python `tenacity` library — declarative retry + circuit-breaker for custom
  agent code; works with any framework
- `resilience4j` (JVM) / `polly` (.NET) — battle-tested circuit-breaker libraries
  for managed-runtime agent code

**Harness HA**
- AWS Bedrock AgentCore — runtime HA managed natively; multi-AZ by default;
  no customer-side HA design needed; check SLA against your requirement
- Self-managed harness on ECS / EKS — Application Load Balancer + auto-scaling
  target group; session affinity via sticky sessions if stateful
- Lambda (serverless harness) — inherently multi-AZ; cold-start latency is the
  tradeoff to validate against your session-start SLA

**Multi-region model failover**
- Amazon Bedrock cross-region inference profiles — single API call, Bedrock
  routes to available capacity across regions; removes per-region capacity
  management for Bedrock-hosted models
- LiteLLM multi-target routing — configure provider targets per region; automatic
  failover on HTTP 5xx or timeout
- AWS Route 53 health checks + weighted routing — for self-hosted model endpoints;
  route traffic away from an unhealthy regional endpoint automatically

**Graceful degradation (MCP server isolation)**
- MCP Gateway (AgentCore Gateway or self-managed) — per-server health state;
  mark a server unavailable without affecting the session's other tool calls
- Per-server circuit-breaker in the MCP gateway code — same tenacity/resilience4j
  patterns applied at the tool-dispatch layer

## Connects to

- [Model Gateway](../gateway/modelgw.md) — deployment cooldown and provider
  fallback are implemented at the gateway; resilience policy drives gateway config
- [Observability & Audit](observability.md) — resilience without observability is
  invisible; circuit-breaker state, retry counts, and fallback events must be
  surfaced in traces and alerts
- [Cost Management](cost.md) — multi-provider fallback and retry storms have cost
  implications; count retries against quota to prevent runaway spend during
  degraded periods
- [Session Economics](session-economics.md) — a session interrupted by a provider
  outage should not consume quota for the failed period; design quota attribution
  to exclude failed calls
