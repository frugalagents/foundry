---
type: platform-component
title: Observability & Audit
description: traces · evals · audit trail
group: ops
tags: [ops, observability]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

End-to-end traces of every step and tool/model call, plus an audit trail for
compliance — spanning every layer above. This is a runtime, continuous
concern over live traffic — distinct from [Agent Evals & Quality Harness](../quality/evals.md),
which gates a *change* before it ships, against known tasks, not live
traffic.

## Decisions

**Audit requirements?**
- Standard logs to a SIEM — sufficient for most non-regulated deployments
- Immutable, tamper-evident audit trail — needed for regulated
  environments where "the log itself could have been altered" is an
  unacceptable gap

**Telemetry format and destination?**
- Vendor-specific dashboards only — simplest, locks observability data into
  one provider's tooling
- Standardized OpenTelemetry-compatible export — lets telemetry integrate
  with an existing monitoring stack rather than requiring a second one
  specific to the agent platform

**What gets traced, by default vs. opt-in?**
- Built-in metrics (session count, latency, duration, token usage, error
  rate) — a reasonable default with no additional instrumentation
- Custom spans/traces and metrics — requires instrumenting the agent code
  beyond the built-in defaults, needed when the built-in metrics don't
  cover a specific workflow's failure modes

## Principles

- Trace every step end-to-end — reconstructing "what happened" after the
  fact should not require piecing together partial signals from multiple
  uncorrelated sources
- Immutable audit trail, exportable to a SIEM — the export requirement and
  the immutability requirement are both real for a regulated deployment,
  not substitutes for each other
- Rich metadata tagging on traces (session, agent, tool) is what makes
  large-scale issue investigation tractable — a trace without correlatable
  metadata is much less useful at scale than one with it
- This component observes what already happened; it does not gate a
  release — that's [Agent Evals & Quality Harness](../quality/evals.md)'s job.
  Don't conflate the two when deciding "do we have quality coverage" —
  runtime observability alone doesn't answer that.

## Connects to

- Receives call traces from the [MCP Gateway](../gateway/mcpgw.md) and
  [Model Gateway](../gateway/modelgw.md)
- Distinct from, and not a substitute for, [Agent Evals & Quality Harness](../quality/evals.md)
- Feeds [Cost Management](cost.md) and [Token Economics](token.md) with the
  same underlying telemetry, viewed through a cost lens rather than a
  debugging lens

## Sources

- [AgentCore Observability: Observe your agents and resources](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.md) — checked 2026-08-12 — supports: built-in default metrics (session count, latency, duration, token usage, error rate) available without extra instrumentation, standardized OpenTelemetry-compatible telemetry export for integration with an existing observability stack, rich metadata tagging/filtering for issue investigation at scale, and the distinction between built-in metrics and custom span/trace/metric instrumentation as an opt-in extension
