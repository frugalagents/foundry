---
type: advisory-decision-slice
title: Regional Compliance Telemetry Boundary
description: force an explicit telemetry and approval posture for EU works-council or employee-monitoring sensitive deployments
group: decision-slices
tags: [decision-slice, regional-compliance, works-council, telemetry]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "For EU populations subject to works-council or GDPR employee-monitoring constraints, will platform telemetry stay aggregate-by-team by default or expose individual developer dashboards?"
decision-domain: compliance_overlay
priority: 10
requires: [access/regional-compliance, ops/observability]
advisory:
  slice: true
  fact-rules:
    - key: works_council_required
      value: true
      match-any: [works council, betriebsrat, co-determination, ondernemingsraad, cse approval]
      fact-text: "A works-council or equivalent employee-monitoring approval path appears to be in scope."
    - key: eu_engineering_population
      value: true
      match-any: [germany, netherlands, france, eu developers, european offices, eu engineering]
      fact-text: "EU engineering populations appear to be in scope."
    - key: telemetry_posture
      value: aggregate_only
      match-any: [aggregate by team, aggregate-only, team-level only, no individual dashboards, no per-developer dashboards, no individual productivity metrics, team-level metrics only]
      fact-text: "The telemetry posture is being framed around aggregate team-level visibility rather than individual dashboards."
    - key: telemetry_posture
      value: individual_visible
      match-any: [per-developer dashboards, manager dashboards, individual usage metrics, individual productivity metrics, management-visible telemetry]
      fact-text: "Individual developer telemetry is currently being treated as visible management data."
  activate:
    requires-facts-any: [works_council_required, eu_engineering_population]
  output:
    decision-focus: compliance_overlay
    question:
      id: regional-compliance-telemetry
      text: "For EU populations subject to works-council or GDPR employee-monitoring constraints, will platform telemetry stay aggregate-by-team by default or expose individual developer dashboards?"
      why-it-matters: "This determines whether the rollout is even approvable in jurisdictions where employee-monitoring design choices must be negotiated before deployment."
      decision-domain: compliance_overlay
    recommendation: "Design EU-facing telemetry for aggregate team visibility by default, with individual access limited to the developer and tightly-scoped security workflows. Do not let management dashboards drive the data model."
    risks:
      - "Individual developer dashboards can turn a platform rollout into a works-council blocker or a GDPR employee-monitoring dispute."
    options:
      - path: decision/regional-compliance/aggregate-team-telemetry
        title: Aggregate team telemetry
        summary: Keep management reporting at team or business-unit level and avoid per-developer productivity views.
        decision-domain: compliance_overlay
        position: recommended
      - path: decision/regional-compliance/individual-self-service-only
        title: Individual self-service only
        summary: Allow the developer to see their own session data while management sees only aggregates.
        decision-domain: compliance_overlay
        position: viable
      - path: decision/regional-compliance/management-visible-individual-telemetry
        title: Management-visible individual telemetry
        summary: Surface per-developer activity and usage data in management dashboards.
        decision-domain: compliance_overlay
        position: deferred
  resolutions:
    - when-facts-all: [works_council_required, telemetry_posture=aggregate_only]
      decision: "EU employee-monitoring sensitive populations will use aggregate-by-team telemetry by default rather than management-visible individual dashboards."
    - when-facts-all: [eu_engineering_population, telemetry_posture=aggregate_only]
      decision: "EU employee-monitoring sensitive populations will use aggregate-by-team telemetry by default rather than management-visible individual dashboards."
---

This slice exists because regional compliance is not just about region selection.
For EU employee populations, the decisive architecture question is often the
telemetry model: what gets logged, who can see it, and whether that posture is
approvable before rollout.

## Connects to

- [Regional Compliance & Works Council](../access/regional-compliance.md)
- [Observability & Audit](../ops/observability.md)
