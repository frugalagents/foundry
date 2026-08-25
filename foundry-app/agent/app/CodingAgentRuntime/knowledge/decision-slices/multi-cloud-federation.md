---
type: advisory-decision-slice
title: Multi-Cloud Governance Boundary
description: force an explicit decision on whether Azure or GCP populations become governed federated lanes or temporary migration exceptions
group: decision-slices
tags: [decision-slice, multi-cloud, federation, acquisition]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Do Azure or GCP populations need governed cloud-resident lanes under the same policy model, or are they short-lived migration exceptions?"
decision-domain: multi_cloud
priority: 10
requires: [ops/multi-cloud-governance, ops/federation, access/idp-federation]
advisory:
  slice: true
  fact-rules:
    - key: multi_cloud_required
      value: true
      match-any: [multi-cloud, azure, gcp, vertex ai, azure devops, existing azure, existing gcp]
      fact-text: "Non-AWS cloud footprints appear to be in scope for the platform."
    - key: no_forced_aws_migration
      value: true
      match-any: [without aws migration, no aws migration, keep on azure, keep on gcp, stay on azure, stay on gcp, cloud-resident, no forced migration]
      fact-text: "At least one population expects governance parity without a forced AWS migration."
    - key: multi_cloud_governance_model
      value: federated
      match-any: [same policy across clouds, governance parity, federated platform, same identity across clouds, same audit across clouds, one platform across clouds]
      fact-text: "The target state appears to be a federated governance model across clouds."
    - key: multi_cloud_governance_model
      value: temporary_overlay
      match-any: [temporary overlay, short-term exception, migrate later, six month migration, 6 month migration, short-lived migration exception]
      fact-text: "The non-AWS footprint is currently being treated as a temporary migration exception."
  activate:
    requires-facts-all: [multi_cloud_required]
  output:
    decision-focus: multi_cloud
    question:
      id: multi-cloud-governance-boundary
      text: "Do the Azure or GCP populations need governed cloud-resident lanes under the same identity, policy, and audit model, or are they short-lived migration exceptions?"
      why-it-matters: "This determines whether multi-cloud is part of the platform architecture or merely a migration artifact with an exit date."
      decision-domain: multi_cloud
    recommendation: "Do not force an AWS migration just to preserve architectural neatness. If Azure or GCP footprints will persist, govern them as federated lanes with shared identity, policy, and evidence requirements."
    risks:
      - "Treating a durable Azure or GCP footprint as a temporary exception will create long-lived governance drift and surprise migration debt."
    options:
      - path: decision/multi-cloud/federated-governed-lanes
        title: Federated governed lanes
        summary: Keep Azure or GCP populations cloud-resident but governed under the same identity, policy, and audit canon.
        decision-domain: multi_cloud
        position: recommended
      - path: decision/multi-cloud/temporary-overlay-with-exit-date
        title: Temporary overlay with exit date
        summary: Accept a short-lived overlay on the non-AWS footprint while a dated migration plan is executed.
        decision-domain: multi_cloud
        position: viable
      - path: decision/multi-cloud/force-immediate-migration
        title: Immediate AWS migration
        summary: Require all non-AWS populations to migrate before the platform can standardize.
        decision-domain: multi_cloud
        position: deferred
  resolutions:
    - when-facts-all: [multi_cloud_required, no_forced_aws_migration, multi_cloud_governance_model=federated]
      decision: "Azure and GCP populations remain cloud-resident but are governed as federated lanes under one identity, policy, and audit model."
---

This slice exists because acquisition and cloud-diversity signals should not be
left as background context. They change whether the architecture is a single
instance with migration pressure or a federated platform with durable cross-cloud
governance.

## Connects to

- [Multi-Cloud Governance](../ops/multi-cloud-governance.md)
- [Platform Instance Federation](../ops/federation.md)
- [IdP Federation at Scale](../access/idp-federation.md)
