---
type: advisory-decision-slice
title: Exception Governance for Default Tooling
description: force explicit population-scoped exception lanes once the target state becomes default-plus-exceptions
group: decision-slices
tags: [decision-slice, operating-model, exceptions, governance]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Which developer populations actually need formal exception lanes, and will those exceptions be bounded and reviewable rather than personal carve-outs?"
decision-domain: exception_governance
priority: 11
requires: [harness-selection/multi-harness-governance, access/policy-tiers]
advisory:
  slice: true
  fact-rules:
    - key: exception_scope
      value: named_populations
      match-any: [named populations, named teams, specific populations, specific teams, regulated-repo contributors, platform engineers, contractor population]
      fact-text: "Exception demand is being framed around named populations rather than open-ended personal carve-outs."
    - key: exception_scope
      value: personal_or_unbounded
      match-any: [personal exceptions, individual exceptions, case by case, ad hoc exceptions, open-ended exceptions, permanent exceptions]
      fact-text: "Exception demand currently looks person-by-person or open-ended."
    - key: exception_review
      value: time_bounded
      match-any: [time-bounded, time bounded, expires, expiration, renewal, quarterly review, annual review]
      fact-text: "Exception lanes are expected to be time-bounded and renewed deliberately."
  activate:
    requires-facts-all: [operating_model=default_plus_exceptions]
  output:
    decision-focus: exception_governance
    question:
      id: exception-governance-named-lanes
      text: "Which developer populations actually need formal exception lanes, and are those lanes time-bounded and reviewable rather than personal carve-outs?"
      why-it-matters: "A default-plus-exceptions model only stays governable if the exceptions are population-scoped, explicit, and revocable."
      decision-domain: exception_governance
    recommendation: "Do not let 'exceptions' mean ad hoc user-by-user variance or personal carve-outs. Convert them into named population lanes with explicit entry criteria, expiry, and review."
    risks:
      - "Personal or open-ended exceptions will become shadow standards and undermine the default operating model."
    options:
      - path: decision/exception-governance/named-population-lanes
        title: Named population exception lanes
        summary: Restrict exceptions to defined developer populations with explicit review and renewal.
        decision-domain: exception_governance
        position: recommended
      - path: decision/exception-governance/repo-scoped-exceptions
        title: Repo-scoped exceptions
        summary: Allow exceptions only for named repo classes or regulated workloads, not individual preference.
        decision-domain: exception_governance
        position: viable
      - path: decision/exception-governance/personal-exceptions
        title: Personal exceptions
        summary: Let exceptions be handled case by case for individual developers or managers.
        decision-domain: exception_governance
        position: deferred
  resolutions:
    - when-facts-all: [operating_model=default_plus_exceptions, exception_scope=named_populations, exception_review=time_bounded]
      decision: "Formal exception paths are limited to named populations and governed as time-bounded lanes rather than personal carve-outs."
---

This slice exists to make "default plus exceptions" concrete. If the user says
they want one standard tool with exception paths, the advisory flow should force
the next architecture decision: who those exceptions are for, and whether the
exceptions are governable enough to preserve the default.

## Connects to

- [Multi-Harness Governance](../harness-selection/multi-harness-governance.md)
- [Policy Tiers](../access/policy-tiers.md)
