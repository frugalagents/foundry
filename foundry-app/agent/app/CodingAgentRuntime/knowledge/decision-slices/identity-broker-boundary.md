---
type: advisory-decision-slice
title: Identity Broker Boundary
description: force an explicit decision on whether the platform trusts one brokered identity boundary across BUs and acquisitions
group: decision-slices
tags: [decision-slice, identity, federation, acquisition]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Will the platform trust one brokered identity boundary across upstream IdPs, or integrate directly with each BU identity source?"
decision-domain: identity_boundary
priority: 9
requires: [access/identity, access/idp-federation]
advisory:
  slice: true
  fact-rules:
    - key: multiple_idps
      value: true
      match-any: [multiple idps, more than one identity provider, separate identity providers, acquired bu, acquired company, legacy ad forest, active directory forest, acquisition identity]
      fact-text: "More than one upstream identity source appears to be in scope."
    - key: multiple_idps
      value: true
      match-all: [okta, entra]
      fact-text: "More than one upstream identity source appears to be in scope."
    - key: identity_broker
      value: central_broker
      match-any: [iam identity center, central identity broker, one broker, single issuer, normalize claims, brokered identity]
      fact-text: "The target state appears to be one brokered identity boundary with normalized claims."
  activate:
    requires-facts-all: [multiple_idps]
  output:
    decision-focus: identity_boundary
    question:
      id: identity-boundary-broker
      text: "Will the platform trust one central identity broker that normalizes claims across upstream IdPs, or are you expecting each BU identity source to integrate independently?"
      why-it-matters: "The identity trust boundary determines how every later access, jurisdiction, and regulated-repo rule will actually be enforced."
      decision-domain: identity_boundary
    recommendation: "Do not couple platform rollout to monolithic IdP consolidation. Prefer one brokered trust boundary with normalized claims unless there is a hard legal reason not to."
    risks:
      - "Direct per-BU identity integrations create policy drift and make regulated attribute enforcement brittle."
    options:
      - path: decision/identity-boundary/central-broker
        title: Central identity broker
        summary: Normalize claims from upstream IdPs into one platform trust boundary.
        decision-domain: identity_boundary
        position: recommended
      - path: decision/identity-boundary/staged-broker
        title: Staged broker adoption
        summary: Start with the largest IdPs on the broker and onboard the rest with a formal runbook.
        decision-domain: identity_boundary
        position: viable
      - path: decision/identity-boundary/direct-bu-integrations
        title: Direct BU integrations
        summary: Let each business unit or acquired company integrate its IdP directly to the platform.
        decision-domain: identity_boundary
        position: deferred
  resolutions:
    - when-facts-all: [multiple_idps, identity_broker=central_broker]
      decision: "The platform will trust one brokered identity boundary that normalizes claims across upstream IdPs."
---

This slice exists because identity sprawl is a platform-shaping constraint, not
an implementation detail. If the customer has acquisitions, separate BUs, or
legacy directories, the advisor should surface the trust-boundary decision early
instead of assuming identity can be sorted out later.

## Connects to

- [Identity & Access](../access/identity.md)
- [IdP Federation at Scale](../access/idp-federation.md)
