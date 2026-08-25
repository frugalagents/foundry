---
type: platform-component-group
title: Ops
description: runtime observability, cost attribution, and token efficiency
group: ops
tags: [ops]
timestamp: 2026-08-12T00:00:00Z
status: candidate
decision-domain: audit_ops
priority: 4
implies: [ops/observability, ops/cost, ops/token, ops/session-economics, ops/resilience]
---

Three components sharing overlapping telemetry, viewed through three
different lenses: debugging/audit ([Observability & Audit](observability.md)),
attribution/chargeback ([Cost Management](cost.md)), and efficiency
optimization ([Token Economics](token.md)). None of the three substitutes
for another.

## Components

- [Observability & Audit](observability.md) — traces, evals, audit trail. Written.
- [Cost Management](cost.md) — attribution, chargeback. Written.
- [Token Economics](token.md) — metering, cache, right-sizing. Written.
