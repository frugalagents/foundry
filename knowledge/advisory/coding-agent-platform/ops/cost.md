---
type: platform-component
title: Cost Management
description: attribution · chargeback
group: ops
tags: [ops, cost]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Attributes spend to a user/team/repo, powers chargeback/showback, and
tracks budgets against the quotas set by
[Quota & Rate Limits](../access/quota.md). Where the money is actually seen
and capped depends heavily on *how* the platform is deployed — a per-seat
subscription, a metered API/console workspace, or a cloud-provider account —
each has different visibility and control surfaces, and per-user
attribution isn't automatic in every one of them.

## Decisions

**Cost model?**
- Showback — visibility only, no enforcement; useful as a first step before
  committing to a chargeback model
- Chargeback — bill teams for their actual usage; requires per-user/team
  attribution to already be reliable, or chargeback numbers will be
  disputed
- Hybrid — showback broadly, with hard caps only where actually needed

**How is spend actually attributed per user/team?**
- Built into the platform's own usage dashboard — works out of the box on
  a seat-based or console/workspace deployment, but stops working the
  moment usage moves to a cloud-provider-billed deployment, since the
  provider bills the org, not the vendor, and per-user attribution isn't
  sent back to the vendor's own dashboards in that case
- OpenTelemetry export to your own observability stack — works regardless
  of deployment model, since it's collected independently of how billing
  happens; the one option that's deployment-model-agnostic
- A gateway/proxy in front of all calls that tracks spend per key/identity —
  necessary specifically for cloud-provider-billed deployments if
  per-user attribution matters, since neither the provider's billing
  console nor the vendor's dashboard gives you that view natively there

**Where are spend limits actually set?**
- Platform-native spend limits (seat allowance, workspace limit) — simplest,
  only available on seat-based or console/workspace deployments
- Cloud provider's own budget controls — the mechanism for a
  cloud-provider-billed deployment, since the platform vendor doesn't see
  or control that spend directly

## Principles

- Attribute every dollar to an owner — a cost with no attributable owner
  can't be showed back or charged back to anyone
- **Per-user cost attribution is not automatic under every deployment
  model** — it's native to seat-based and console/workspace deployments,
  but requires an explicit extra step (OTel export, or a gateway/proxy) once
  billing moves to a cloud provider's own account. Don't assume the
  platform's built-in dashboard covers this in every configuration.
- Dashboards per team; alert on anomalies — a cost spike is often the
  first visible signal of a runaway loop or a misconfigured automation,
  not just a billing surprise

## Connects to

- Tracks budgets against the ceilings set by [Quota & Rate Limits](../access/quota.md)
- Shares underlying telemetry with [Observability & Audit](observability.md)
  and [Token Economics](token.md), viewed through a cost/attribution lens

## Sources

- [Manage costs effectively](https://code.claude.com/docs/en/costs) — checked 2026-08-12 — supports: three distinct deployment models (seat-based subscription, metered console/API workspace, cloud-provider-billed) with different native spend-visibility and per-user-attribution capabilities per model; OpenTelemetry export and a self-hosted gateway/proxy as the two deployment-agnostic ways to recover per-user attribution when billing moves to a cloud provider's own account; workspace-level and seat-level spend limits as the platform-native capping mechanisms, versus the cloud provider's own budget controls when billed that way
