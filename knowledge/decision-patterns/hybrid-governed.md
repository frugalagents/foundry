---
schema_version: "1.0"
kind: DecisionPattern
id: decision-pattern:hybrid-governed
title: Hybrid governed platform
summary: Combine customer-governed execution and controls with selected SaaS experience or orchestration services.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - bundle-template:hybrid-governed
  - customer-governed-execution
  - hybrid-platform
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Approved baseline decision pattern for mixed managed and customer-governed service boundaries.
decision: Keep sensitive execution, identity, policy, evidence, and telemetry in customer-governed services while using SaaS where it materially improves developer experience or delivery speed.
recommended_when:
  - Customer-managed or hybrid execution is required but a SaaS developer experience is acceptable.
  - The organization needs stronger portability than a single-provider managed stack.
  - Identity, policy, telemetry, and incident ownership can span provider boundaries.
avoid_when:
  - The organization requires a single-provider support and failure domain.
  - Cross-provider identity, networking, telemetry, and incident operations cannot be owned.
  - Data transfer across the SaaS and customer boundary is prohibited.
tradeoffs:
  - The pattern balances experience and control at the cost of cross-provider operational complexity.
  - Portability improves only where contracts and evidence remain provider-neutral.
  - Split ownership requires explicit responsibility, telemetry correlation, and failure handling.
supporting_claim_ids:
  - claim:architecture-first-authority
---

# Hybrid Governed Platform

Use this pattern when the customer needs a governed execution boundary but can
benefit from selected SaaS capabilities. Treat every provider crossing as an
explicit identity, data, telemetry, support, and failure boundary.
