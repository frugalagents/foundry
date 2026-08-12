---
schema_version: "1.0"
kind: DecisionPattern
id: decision-pattern:aws-governed
title: AWS governed managed platform
summary: Use AWS-managed governance, execution, model access, observability, and security services as the primary coding-agent platform boundary.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - bundle-template:aws-governed
  - customer-governed-execution
  - managed-platform
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Approved baseline decision pattern for a governed AWS operating model.
decision: Place the primary coding-agent control, execution, identity, policy, evidence, and observability boundaries in customer-governed AWS services.
recommended_when:
  - Customer-managed or hybrid execution is required.
  - Security controls, auditability, and operational integration outweigh fastest initial delivery.
  - The organization already operates AWS identity, networking, security, and observability controls.
avoid_when:
  - Provider portability is a dominant requirement.
  - The team cannot own cloud platform integration and lifecycle operations.
  - A vendor-managed-only service boundary is mandatory.
tradeoffs:
  - Strong governance and operational integration increase platform engineering work.
  - Managed AWS services reduce infrastructure ownership but retain AWS service coupling.
  - Delivery is usually slower than a SaaS-first launch and faster than a fully self-hosted platform.
supporting_claim_ids:
  - claim:architecture-first-authority
  - claim:bedrock-managed-inference
---

# AWS Governed Managed Platform

Use this pattern when the customer needs a controlled enterprise platform
boundary and already has an AWS operating model that can own identity,
networking, security, observability, and service lifecycle decisions.

The pattern is advisory. Product eligibility, region support, isolation
strength, quotas, and service compatibility must still be established by
current scoped claims.
