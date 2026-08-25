---
type: platform-component
title: Progressive Trust
description: teams earning relaxed guardrails over time based on demonstrated responsible usage
group: access
tags: [access, governance, progressive-trust, trust-signals, tier-progression]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: probe
trigger: [progressive-trust, earn-higher-limits, trust-over-time, auto-tier-upgrade]
decision-question: "Should developers or teams be able to earn relaxed guardrails and higher quotas over time based on demonstrated responsible usage?"
decision-domain: population_policy
priority: 6
requires: [access/policy-tiers, access/quota]
---

Progressive trust is a governance pattern where teams start under a conservative
posture and earn relaxed guardrails and higher quotas based on demonstrated
responsible usage — rather than through manual discretion alone. It makes the
tier approval workflow a living, data-driven system rather than a one-time gate.

## Model

1. **Baseline** — all new developers start at Standard tier with conservative defaults
2. **Observation window** — platform logs usage patterns for a defined period (e.g.,
   30 days); no action taken
3. **Trust signal accumulation** — clean guardrail record, usage within quota,
   high human-approval rate on actions that required approval
4. **Tier review** — automated flag or scheduled review proposes a tier upgrade
5. **Approval** — platform admin or team lead approves the upgrade
6. **Downgrade path** — policy violation, DLP incident, or sustained spend breach
   triggers a flag that can result in tier downgrade if unresolved

## Trust Signals

**Positive signals:**
- Clean DLP record for N consecutive days
- No guardrail override attempts
- Usage consistently within quota (not regularly hitting the ceiling)
- High human-approval rate on prompted approval actions (agent asks, developer approves)

**Negative signals (trigger review):**
- Any confirmed DLP violation
- Guardrail override attempt
- Spend limit breach exceeding the tier ceiling by more than X%
- Unusual tool call patterns (high-volume calls to write tools, unusual access times)

## Decisions

**Is progressive trust automated or manual?**
- Fully manual — simpler to implement; slow to scale; suitable for small teams
- Automated flag + human approval — balances scale with oversight; recommended
- Fully automated — highest scale; highest risk of gaming; use only with strong
  anomaly detection in the negative-signal pipeline

**What counts as an observation window?**
- Time-based (30 days active usage) — simple; does not reward volume of
  responsible use
- Activity-based (N completed tasks, M sessions) — rewards engagement;
  harder to game with inactivity

**Is trust per-developer or per-team?**
- Per-developer — granular; more admin overhead
- Per-team — simpler; risk that one developer's record affects the team
- Hybrid: team-level baseline + individual overrides for high-performers

## Stack Options

**Trust signal collection**
- Amazon CloudWatch Metrics — publish custom metrics per developer: DLP
  violation count, guardrail fire rate, spend-vs-cap ratio, approval rate;
  metrics are the raw material for trust signal computation
- AWS Lambda metric aggregator — runs on a schedule (daily/weekly); reads
  CloudWatch metrics, computes trust score per developer, writes result to
  DynamoDB tier-signal table

**Trust review and tier transition trigger**
- Amazon EventBridge scheduled rule — trigger the trust-review Lambda on a
  defined cadence (weekly for new developers, monthly for established ones)
- Amazon EventBridge pattern rule — trigger immediately on a negative-signal
  event (GuardDuty finding, DLP violation CloudWatch alarm); feeds the
  downgrade path without waiting for the next scheduled review

**Approval workflow**
- AWS Step Functions + SES — state machine: compute signal → if upgrade-
  eligible, email team lead for approval → on approval, update DynamoDB
  tier assignment → notify developer
- Slack integration via Lambda — post tier-upgrade proposal to a platform-
  admin Slack channel; thumbs-up reaction triggers the tier update; lower
  friction than email for high-velocity teams

**Audit trail for tier changes**
- AWS CloudTrail + DynamoDB Streams — every tier assignment change in
  DynamoDB is streamed to an S3 audit bucket via Kinesis Data Firehose;
  tamper-evident record of who changed what tier and when
- AWS Config — track the state of tier assignment records over time;
  supports compliance queries like "what was this developer's tier on
  date X?"

## Principles

- Progressive trust makes tier assignment a living system — it should improve
  the platform's governance quality over time, not just create a backlog
  of upgrade requests
- Downgrade paths matter as much as upgrade paths — an explicit downgrade policy
  prevents the system from only ever ratcheting toward more permissive
- Tie progressive trust to [Policy Tiers](policy-tiers.md) — trust progression
  is implemented as tier transitions, not as ad-hoc per-developer policy edits
- The trust signal pipeline depends on observability; if audit logs are incomplete,
  trust signals are unreliable

## Connects to

- [Policy Tiers](policy-tiers.md) — trust progression is movement between tiers;
  this node defines the policy; policy-tiers defines the structure
- [Quota & Rate Limits](quota.md) — quota values change as tier changes
- [Observability & Audit](../ops/observability.md) — trust signals are derived from
  audit data; the observability pipeline is the source of truth for this system
