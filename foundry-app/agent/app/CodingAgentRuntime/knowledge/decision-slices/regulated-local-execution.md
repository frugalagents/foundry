---
type: advisory-decision-slice
title: Regulated Repos + Local Execution
description: challenge the platform shape when regulated workloads and local execution requests collide
group: decision-slices
tags: [decision-slice, export-control, local-execution, execution-boundary]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Are the export-controlled repositories isolated to a separate developer population and execution lane, or does the business unit expect local execution for those same workloads?"
decision-domain: execution_boundary
priority: 12
requires: [access/export-control, exec/local]
advisory:
  slice: true
  activate:
    requires-facts-all: [export_control, local_execution_requested]
  output:
    decision-focus: execution_boundary
    question:
      id: execution-boundary-regulated-local
      text: "Are the export-controlled repositories isolated to a separate developer population and execution lane, or does the business unit expect local execution for those same workloads?"
      why-it-matters: "This answer determines whether local execution can stay in scope at all for regulated workloads."
      decision-domain: execution_boundary
    recommendation: "Do not assume a shared local execution pattern for export-controlled workloads. Treat this as a controlled split-boundary decision before locking the platform shape."
    risks:
      - "Local execution may be incompatible with export-controlled workloads unless the regulated population and execution boundary are isolated."
    options:
      - path: decision/execution-boundary/regulated-remote-lane
        title: Isolated remote lane for regulated repos
        summary: Keep export-controlled workloads on a separate remote or microVM execution path and allow local execution only where policy permits.
        decision-domain: execution_boundary
        position: recommended
      - path: decision/execution-boundary/split-local-and-remote
        title: Split local and remote execution by repo class
        summary: Allow local execution for general engineering repos but carve out a controlled remote lane for sensitive code.
        decision-domain: execution_boundary
        position: viable
      - path: decision/execution-boundary/full-local
        title: Unrestricted local execution
        summary: Treat local execution as the default for all workloads, including regulated code.
        decision-domain: execution_boundary
        position: deferred
  resolutions:
    - when-facts-all: [export_control, local_execution_requested, regulated_population_isolated, local_execution_scope=non_regulated_only]
      decision: "Export-controlled workloads stay on a separate controlled lane while local execution is reserved for lower-sensitivity workflows."
---

This slice exists to force an architecture challenge when a customer combines a
regulated workload boundary with a request for local execution. The point is not
to choose a product. The point is to stop the advisory flow from treating those
two statements as compatible by default.

## Connects to

- [Export Control (ITAR / EAR)](../access/export-control.md)
- [Execution — Local](../exec/local.md)
