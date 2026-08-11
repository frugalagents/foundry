---
schema_version: "1.0"
kind: Capability
id: capability:model-routing
title: Governed model routing
summary: Select and invoke an eligible model using policy, workload context, availability, quality, and cost constraints.
lifecycle: active
owner_id: team:platform-advisor
aliases: []
tags:
  - model-access
  - policy
  - routing
effective_from: 2026-08-11
stale_after: 2027-02-11
review:
  status: approved
  reviewer_ids:
    - person:principal-platform-architect
  reviewed_at: 2026-08-11T12:00:00Z
  rationale: Stable provider-neutral capability for controlled access to one or more model providers.
category: model-access
desired_outcomes:
  - select only models eligible for the workload and region
  - make routing rationale and fallback behavior observable
  - balance quality latency availability and cost objectives
---

# Governed Model Routing

## Purpose

Choose an eligible model endpoint for each workload while preserving identity,
policy, data-handling, regional, availability, quality, latency, and economic
constraints.

## Architecture Role

The capability belongs to the model plane. `component:model-gateway` owns the
invocation boundary, while `component:model-catalog` supplies approved model,
provider, region, lifecycle, and constraint metadata.

## Relationship Intent

- Requires a current model catalog and workload policy context.
- Integrates with model providers through versioned invocation interfaces.
- Uses evaluation and telemetry evidence without allowing benchmark rank alone
  to become routing authority.
- May provide failover only between models that remain eligible for the same
  workload constraints.

## Decision Guidance

Recommend centralized routing when the platform supports multiple models,
regions, providers, fallback policies, quotas, or differentiated workload
classes. A direct provider integration can remain appropriate for a constrained
single-model platform when eligibility and lifecycle controls still exist.

Do not encode subjective model preference as a hard compatibility rule.

## Evidence State

This page approves the provider-neutral semantic identity only. Model
availability, features, context limits, pricing, quotas, regional support, and
interface compatibility require separately reviewed and time-scoped claims.
