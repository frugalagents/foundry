---
type: advisory-decision-slice
title: Shared Control Plane Boundary
description: force a decision on whether every harness and exception lane stays on one shared control plane
group: decision-slices
tags: [decision-slice, control-plane, gateway, governance]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Will every approved harness and exception lane stay on one shared control plane for identity, gateway policy, quota, and audit?"
decision-domain: control_plane
priority: 8
requires: [gateway/mcpgw, gateway/modelgw, access/identity, ops/observability]
advisory:
  slice: true
  fact-rules:
    - key: shared_control_plane
      value: true
      match-any: [shared control plane, same control plane, shared controls, one audit path, central logging, common gateway, shared gateway, shared identity and policy]
      fact-text: "The target state appears to keep approved lanes on one shared control plane."
    - key: control_plane_bypass_requested
      value: true
      match-any: [direct api keys, direct provider access, bypass gateway, separate credentials, tool-specific credentials, direct to provider, each tool connects directly]
      fact-text: "At least one lane is asking to bypass the shared control plane."
  activate:
    requires-facts-any: [operating_model=default_plus_exceptions, operating_model=multi_harness_governed, local_execution_requested]
  output:
    decision-focus: control_plane
    question:
      id: control-plane-shared-boundary
      text: "Will every approved harness and exception lane still use the same identity, gateway, policy, quota, and audit path, or are any lanes allowed to bypass the shared control plane?"
      why-it-matters: "If exception lanes bypass the shared control plane, the architecture stops being one platform and becomes a collection of disconnected tools."
      decision-domain: control_plane
    recommendation: "Keep every approved lane on one shared control plane even when execution or harness choices differ. Challenge any request for direct provider credentials or side-door integrations."
    risks:
      - "Direct provider or tool integrations outside the shared control plane will break audit consistency, policy enforcement, and cost attribution."
    options:
      - path: decision/control-plane/shared-governance
        title: Shared control plane for all lanes
        summary: Keep identity, model/tool gateways, quota, and audit common across the default and every exception path.
        decision-domain: control_plane
        position: recommended
      - path: decision/control-plane/shared-controls-split-execution
        title: Shared controls with split execution
        summary: Permit different execution lanes, but keep identity, gateway policy, and audit centralized.
        decision-domain: control_plane
        position: viable
      - path: decision/control-plane/per-lane-bypass
        title: Per-lane bypasses
        summary: Let certain tools or exception lanes connect to providers and enterprise systems directly.
        decision-domain: control_plane
        position: deferred
  resolutions:
    - when-facts-all: [shared_control_plane]
      decision: "All approved harnesses and exception lanes stay on one shared control plane for identity, gateway policy, quota, and audit."
---

This slice exists to keep the architecture from fragmenting. Multiple harnesses,
regulated lanes, or local execution can still be one platform, but only if the
identity boundary, gateways, policy, quota, and audit model remain shared.

## Connects to

- [MCP Gateway](../gateway/mcpgw.md)
- [Model Gateway](../gateway/modelgw.md)
- [Identity & Access](../access/identity.md)
- [Observability & Audit](../ops/observability.md)
