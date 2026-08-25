---
type: platform-component
title: Policy Tiers
description: differentiated quota and guardrail enforcement across developer populations
group: access
tags: [access, governance, policy-tiers, innovation-lab, exception-model]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [innovation-lab, policy-exception, tiered-access, different-teams-different-limits, contractor-access, spend-exception]
decision-question: "Do different teams or developer populations need differentiated quota limits, guardrail settings, or tool access — and how is that governed?"
decision-domain: population_policy
priority: 8
requires: [access/identity, access/quota]
---

Not all developers should sit under identical quota and guardrail settings.
Policy tiers let you run differentiated enforcement across your developer
population — without building separate platform instances or creating
unaudited ad-hoc exceptions.

## Tier Model

| Tier | Typical members | Quota posture | Guardrail posture | Tool access |
|---|---|---|---|---|
| Standard | Majority of developers | Default monthly spend cap | Full filtering + DLP | Approved tool set |
| Innovation lab | Trusted R&D, platform team | Higher or uncapped quota | Relaxed filtering; still fully logged | Extended tool access including experimental |
| Restricted | Contractors, offshore, sensitive-repo access | Lower quota; narrower tool set | Stricter output review; tighter allow-list | Minimal approved tools |
| Executive / admin | Platform admins | Management plane only | n/a — no agent coding access | Admin console only |

## Decisions

**Who assigns a developer to a non-standard tier?**
- Platform admin only — tightest control; slow at scale
- Team lead nominates, platform admin approves — scales to hundreds of developers
- Self-serve with approval workflow — most scalable; most administration overhead

**How are exceptions handled?**
- Time-bounded approval (e.g., 90-day innovation lab membership, renewable) —
  most auditable; prevents permanent drift toward over-grant
- Permanent tier upgrade — simpler; harder to recover from; requires periodic
  audit to catch stale grants

**What triggers a tier downgrade or review?**
- Manual periodic review (quarterly) — slow but simple
- Automated flag: sustained spend-limit breach, DLP violation, or guardrail
  override attempt → flag for review → tier downgrade if unresolved within N days

## The Innovation Lab Pattern

The canonical answer to "can I let some developers bypass spend limits while
others stay capped" is: create a named Innovation Lab tier with documented
justification and a time limit — not an ad-hoc exception per developer.

Properties of a well-governed innovation lab tier:
- Named group in the admin console with a defined membership list
- Audit logging identical to or stricter than standard tier (relaxed guardrails
  ≠ reduced logging)
- Higher quota, not unlimited — even the lab tier has a ceiling; just a much
  higher one
- Renewal gate: membership requires re-justification every N months

## Stack Options

**Tier enforcement (AWS managed / SaaS)**
- Claude Code enterprise admin console — configure spend limits and allowed
  tools per user group; groups map directly to policy tiers; operators assign
  users to groups; AND-logic (per-user cap + per-group cap) enforces the tier
  ceiling even when individual limits are raised
- Claude Code server-managed settings — JSON-based policy file applied to
  defined user populations; supports different model access, tool permissions,
  and guardrail configurations per group; version-controlled and deployed via
  the admin API

**Tier enforcement (custom on AWS)**
- Amazon Cognito user groups + Lambda authorizer — assign developers to
  Cognito groups matching tier names; Lambda authorizer checks group membership
  on every harness API call and injects the tier as a context attribute for
  quota enforcement and guardrail selection
- DynamoDB tier assignment table — `{developer_id → tier, effective_from,
  expiry}` record; the quota enforcement layer reads this at call time to
  apply the right limits; simple to update for tier transitions; supports
  time-bounded assignments natively via TTL

**Quota enforcement per tier**
- Amazon API Gateway usage plans — define per-tier request rate and burst
  limits; associate developer API keys with usage plans matching their tier;
  enforced at the API Gateway layer before traffic reaches the harness
- Custom quota Lambda — track spend per developer per tier in DynamoDB with
  atomic counters; block requests when the tier ceiling is hit; supports
  the alert → throttle → hard-block escalation sequence

**Tier transition workflow**
- AWS Step Functions — model the approval workflow (nominate → approve →
  assign → notify) as a state machine; integrates with EventBridge for
  time-bounded expiry and renewal reminders
- Jira / ServiceNow ticket → Lambda webhook — simpler if you already use
  a ticketing system; webhook on ticket resolution triggers the DynamoDB
  tier assignment update

## Principles

- Tiers are policy groups, not identity groups — a developer moves between tiers
  by re-assignment, not re-provisioning; the tier label is the variable
- Innovation lab tier must log everything — relaxed guardrails never mean reduced
  observability; if anything, higher-risk tiers need more audit coverage
- Downgrade paths are as important as upgrade paths — define them explicitly,
  or the system only ratchets toward more permissive over time

## Connects to

- [Quota & Rate Limits](quota.md) — per-tier quota values configured here; the
  AND-logic (per-caller + per-group caps) enforces the tier ceiling even when
  individual caps are raised
- [Guardrails & Policy](guardrails.md) — per-tier filtering configuration; the
  guardrail engine needs a caller-tier signal to apply differential rules
- [Progressive Trust](progressive-trust.md) — tiers are the mechanism; progressive
  trust is the policy for how developers move between them over time
- [Observability & Audit](../ops/observability.md) — tier assignment changes
  must be audited identically to policy changes

## Sources

- [Claude Code spend limits](https://code.claude.com/docs/en/claude-apps-gateway-spend-limits) — checked 2026-08-12 — per-caller and per-group spend cap enforcement; AND-logic for combined limits
- [Claude Code server-managed settings](https://code.claude.com/docs/en/server-managed-settings) — checked 2026-08-12 — operator-set policy overrides for different user populations
