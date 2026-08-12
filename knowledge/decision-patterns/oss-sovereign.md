---
schema_version: "1.0"
kind: DecisionPattern
id: decision-pattern:oss-sovereign
title: Open-source sovereign platform
summary: Operate the coding-agent control and execution planes on customer-managed open-source infrastructure.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - bundle-template:oss-sovereign
  - customer-operated
  - sovereignty
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Approved baseline decision pattern for sovereignty-led customer-operated platforms.
decision: Run the primary coding-agent control, execution, model, tool, evidence, and observability boundaries on customer-operated open-source infrastructure.
recommended_when:
  - Customer control, sovereignty, customization, or air-gapped operation is mandatory.
  - The organization has mature Kubernetes, security, supply-chain, and SRE capabilities.
  - Operational ownership is an accepted strategic cost.
avoid_when:
  - Fastest time to value or minimal platform operations is the primary objective.
  - The organization cannot sustain patching, upgrades, capacity, recovery, and incident response.
  - Managed-service certifications or support obligations are mandatory.
tradeoffs:
  - Maximum control and customization create the largest operational and security ownership surface.
  - Software license savings do not imply lower total platform cost.
  - Sovereignty improves only when model, telemetry, artifact, and support paths remain inside the required boundary.
supporting_claim_ids:
  - claim:architecture-first-authority
  - claim:self-hosted-residency
---

# Open-Source Sovereign Platform

Use this pattern only when sovereignty and customer control justify owning the
full runtime and supply-chain lifecycle. Kubernetes availability alone is not
evidence of the required operational maturity.
