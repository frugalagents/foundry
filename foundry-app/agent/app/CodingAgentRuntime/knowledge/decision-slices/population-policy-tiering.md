---
type: advisory-decision-slice
title: Population Policy Tiering
description: force explicit named policy tiers once the platform shape is shared but populations need different controls
group: decision-slices
tags: [decision-slice, population-policy, policy-tiers, governance]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Which named developer populations need differentiated quota, guardrail, or tool-access tiers, and are those tiers governed rather than ad hoc?"
decision-domain: population_policy
priority: 8
requires: [access/policy-tiers, access/quota, access/guardrails]
advisory:
  slice: true
  fact-rules:
    - key: differentiated_populations
      value: true
      match-any: [contractors, contractor population, platform engineers, innovation lab, restricted population, offshore teams, regulated population, different guardrails, different quota limits, different tool access]
      fact-text: "Different developer populations appear to need differentiated controls."
    - key: tier_assignment_model
      value: named_tiers
      match-any: [named tiers, policy tiers, standard tier, innovation lab, restricted tier, contractor tier, trusted tier]
      fact-text: "Population differentiation is being framed as named policy tiers rather than ad hoc exceptions."
    - key: tier_assignment_model
      value: ad_hoc_exceptions
      match-any: [ad hoc exceptions, case by case, manager discretion, personal exceptions, one-off exceptions]
      fact-text: "Population differentiation is currently being framed as ad hoc exceptions."
    - key: tier_duration
      value: time_bounded
      match-any: [90-day, 90 day, time-bounded, time bounded, quarterly review, expires, renewable, renewal]
      fact-text: "Non-standard tiers are expected to be time-bounded and renewed deliberately."
  activate:
    requires-facts-all: [shared_control_plane]
    requires-facts-any: [operating_model=default_plus_exceptions, operating_model=multi_harness_governed, differentiated_populations]
  output:
    decision-focus: population_policy
    question:
      id: population-policy-tiering
      text: "Which named developer populations need differentiated quota, guardrail, or tool-access tiers, and will those tiers be governed as named groups rather than ad hoc exceptions?"
      why-it-matters: "A shared control plane only stays coherent if population differences are expressed as explicit policy tiers instead of hidden carve-outs."
      decision-domain: population_policy
    recommendation: "Convert population differences into named policy tiers with explicit quota, guardrail, and tool-access posture. Do not let contractors, platform engineers, or regulated teams drift into unmanaged one-off exceptions."
    risks:
      - "Ad hoc population differences will create shadow policies that the shared control plane cannot explain or audit."
    options:
      - path: decision/population-policy/named-policy-tiers
        title: Named policy tiers
        summary: Map populations such as standard, contractor, innovation-lab, and regulated users to explicit policy groups.
        decision-domain: population_policy
        position: recommended
      - path: decision/population-policy/time-bounded-elevations
        title: Time-bounded elevated tiers
        summary: Permit short-lived higher-access tiers for named populations with renewal and review.
        decision-domain: population_policy
        position: viable
      - path: decision/population-policy/ad-hoc-exceptions
        title: Ad hoc per-user exceptions
        summary: Handle population differences case by case through manual operator decisions.
        decision-domain: population_policy
        position: deferred
  resolutions:
    - when-facts-all: [shared_control_plane, differentiated_populations, tier_assignment_model=named_tiers, tier_duration=time_bounded]
      decision: "Population differences are governed through named, time-bounded policy tiers rather than ad hoc exceptions."
---

This slice exists because once the enterprise has a shared control plane, the
next failure mode is not control bypass but silent population drift. Named tiers
make the governance model explainable: who gets which guardrails, quotas, and
tool access, and for how long.

## Connects to

- [Policy Tiers](../access/policy-tiers.md)
- [Quota & Rate Limits](../access/quota.md)
- [Guardrails & Policy](../access/guardrails.md)
