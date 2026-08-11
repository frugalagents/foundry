---
schema_version: "1.0"
kind: Capability
id: capability:governed-tool-access
title: Governed tool access
summary: Mediate agent access to tools and APIs through identity, policy, validation, and audit controls.
lifecycle: active
owner_id: team:platform-advisor
aliases:
  - capability:tool-gateway
tags:
  - authorization
  - gateway
  - tools
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Stable provider-neutral boundary between agent orchestration and enterprise tools.
category: tool-access
desired_outcomes:
  - authorize every tool invocation against workload context
  - constrain tool inputs and outputs
  - produce attributable and reviewable audit records
---

# Governed Tool Access

## Purpose

Provide a controlled invocation boundary between agents and enterprise tools,
APIs, data services, source control, delivery systems, and external actions.

## Architecture Role

The capability belongs to the tool plane and is primarily owned by
`component:tool-gateway`. It collaborates with workload identity, policy
decision and enforcement, secrets, approvals, and audit components.

## Relationship Intent

- Requires authenticated workload identity and explicit tool authorization.
- Integrates with protocol-specific adapters such as MCP, OpenAPI, and native
  service APIs.
- Supports approval controls but does not replace the approval decision owner.
- Is implemented by an offering only after approved authentication,
  authorization, validation, and audit claims exist.

## Decision Guidance

Recommend a shared gateway when tools cross trust boundaries, require
centralized policy, expose privileged actions, or must be audited consistently.
Local adapters may remain appropriate for low-risk developer-only tools when
the same identity and policy requirements are enforced.

Do not infer enterprise governance merely because a product supports a tool
protocol.

## Evidence State

This page approves the provider-neutral semantic identity only. Protocol
support, authentication modes, policy integration, quotas, and audit behavior
must be established by scoped implementation claims.
