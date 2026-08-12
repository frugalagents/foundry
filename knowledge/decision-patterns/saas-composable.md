---
schema_version: "1.0"
kind: DecisionPattern
id: decision-pattern:saas-composable
title: Composable SaaS platform
summary: Use vendor-managed coding-agent control and execution capabilities with governed enterprise integrations.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - bundle-template:saas-composable
  - managed-experience
  - rapid-delivery
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Approved baseline decision pattern for rapid vendor-managed platform adoption.
decision: Use vendor-managed coding-agent services for the primary experience and execution path while governing enterprise identity, repositories, tools, data, and audit integrations.
recommended_when:
  - Delivery speed and low platform operating effort are dominant objectives.
  - Vendor-managed or hybrid execution is acceptable.
  - Product controls, data handling, regional availability, and audit integration satisfy customer policy.
avoid_when:
  - Customer-controlled execution or strict workload sovereignty is mandatory.
  - Provider portability and replaceability are dominant requirements.
  - Required controls depend on evidence the vendor cannot expose.
tradeoffs:
  - Rapid delivery and low operational burden increase product and vendor dependency.
  - Enterprise integration remains necessary even when the core service is managed.
  - Exit planning, data portability, audit access, and service lifecycle must be governed explicitly.
supporting_claim_ids:
  - claim:architecture-first-authority
---

# Composable SaaS Platform

Use this pattern when the customer can accept vendor-managed boundaries and
values time to value over platform ownership. Validate data handling,
execution isolation, regional availability, audit, and exit requirements
against current product evidence before adoption.
