---
schema_version: "1.0"
kind: DecisionPattern
id: decision-pattern:byop-portable
title: BYOP portable platform
summary: Preserve replaceable provider boundaries through contracts and adapters around customer-selected platform services.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - bundle-template:byop-portable
  - portability
  - persistent-workspaces
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Approved baseline decision pattern for portable and durable coding-agent platforms.
decision: Use explicit platform contracts and adapters so customers can select or replace model, execution, tool, memory, and governance implementations.
recommended_when:
  - Long-running or durable remote workspaces are required.
  - Provider portability and replaceable implementation boundaries are strategic requirements.
  - The platform team can own adapter contracts, conformance tests, and lifecycle management.
avoid_when:
  - Fastest initial delivery is the dominant objective.
  - The organization lacks capacity to maintain integration contracts across providers.
  - A single managed service already satisfies the required control boundary.
tradeoffs:
  - Portability reduces provider coupling but increases integration and conformance work.
  - Durable workspaces improve continuity while expanding state, isolation, patching, and recovery responsibilities.
  - Common contracts can limit access to provider-specific features unless extensions are governed.
supporting_claim_ids:
  - claim:architecture-first-authority
---

# BYOP Portable Platform

Use this pattern when replaceability and durable developer environments are
worth the cost of owning contracts, adapters, and conformance testing.

Portability is not assumed from an interface label. Each implementation must
prove contract compatibility and required control behavior.
