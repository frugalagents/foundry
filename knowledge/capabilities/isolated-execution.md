---
schema_version: "1.0"
kind: Capability
id: capability:isolated-execution
title: Isolated agent execution
summary: Execute agent-generated or untrusted code inside a bounded workload environment.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - code-execution
  - isolation
  - runtime
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Stable provider-neutral capability required by coding-agent platforms that execute code.
category: execution-safety
desired_outcomes:
  - contain untrusted workload behavior
  - enforce workload-specific identity and network boundaries
  - preserve auditable execution context
---

# Isolated Agent Execution

## Purpose

Provide a controlled environment for commands, tests, builds, tools, and code
generated or selected by an agent. Isolation is a workload boundary; it is not
equivalent to prompt filtering or an approval dialog.

## Architecture Role

The capability belongs to the execution plane and is coordinated by
`component:execution-broker`. Runtime choices may include
`component:ephemeral-runtime`, `component:persistent-workspace`,
`component:container-runtime`, or `component:kubernetes-runtime`.

## Relationship Intent

- Requires workload identity, network policy, artifact controls, and audit.
- Is implemented by runtime variants only after an approved isolation claim.
- Is not interchangeable with local execution on an unmanaged endpoint.

## Decision Guidance

Recommend this capability when agents execute untrusted, generated, third-party,
or tenant-specific code. Treat stronger isolation, startup latency, persistence,
privilege, and operator responsibility as separate decision dimensions.

Avoid presenting a remote runtime as inherently isolated. Isolation strength
must be established by scoped implementation claims.

## Evidence State

This page approves the provider-neutral semantic identity only. Product
implementations, isolation strength, limits, regions, and compatibility remain
unapproved until source snapshots and reviewed claims are registered.
