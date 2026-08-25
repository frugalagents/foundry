---
type: platform-component
title: Multi-Harness Governance
description: governing an approved portfolio of coding harnesses under one enterprise control plane
group: harness-selection
tags: [harness-selection, multi-harness, governance, portfolio, exceptions, brownfield]
timestamp: 2026-08-22T00:00:00Z
status: candidate
traversal: conditional
trigger: [multi-harness, multiple tools, multiple harnesses, approved tools, approved harnesses, tool sprawl, harness portfolio, portfolio governance, default plus exceptions, default with exceptions, exception path, coexistence]
trigger_pool: [copilot, github copilot, cursor, claude code, codex]
trigger_pool_min_matches: 2
decision-question: "Is the target state a single standard harness, a governed multi-harness portfolio, or one default harness with formal exception paths?"
decision-domain: operating_model
priority: 10
blocking: true
implies: [access/policy-tiers, access/quota, access/identity, gateway/mcpgw, gateway/modelgw]
advisory:
  slice: true
  fact-rules:
    - key: current_tools
      value-from: matched_trigger_pool_labels
      min-trigger-pool-matches: 1
      label-map:
        github copilot: GitHub Copilot
        copilot: GitHub Copilot
        cursor: Cursor
        claude code: Claude Code
        codex: Codex CLI
      fact-text: "Current tools in scope: {value}."
    - key: multi_tool_current_state
      value: true
      min-trigger-pool-matches: 2
    - key: operating_model
      value: single_standard
      match-any: [single standard, one standard tool, single approved tool, one tool for everyone]
    - key: operating_model
      value: multi_harness_governed
      match-any: [governed multi-harness, multi-harness portfolio, approved portfolio]
    - key: operating_model
      value: default_plus_exceptions
      match-any: [default plus exceptions, default with exceptions, formal exception paths, exception lanes]
  activate:
    requires-facts-all: [multi_tool_current_state]
  output:
    decision-focus: operating_model
    question:
      id: operating-model-current-multi-tool
      text: "Is the target state one standard tool, a governed multi-harness portfolio, or one default tool with formal exception paths?"
      why-it-matters: "Multiple tools are already in play, so the platform should resolve the governance model before comparing products."
      decision-domain: operating_model
    recommendation: "Treat the current state as a multi-tool environment and resolve the operating model before narrowing to products. Until that is explicit, assume shared controls matter more than forcing premature tool uniformity."
    risks:
      - "Multiple approved tools without an explicit operating model will drift into unmanaged exceptions and inconsistent controls."
    options:
      - path: decision/operating-model/multi-harness-governed
        title: Governed multi-harness portfolio
        summary: Several approved tools operate under one shared identity, policy, audit, and quota model.
        decision-domain: operating_model
        position: recommended
      - path: decision/operating-model/default-plus-exceptions
        title: One default with formal exceptions
        summary: Standardize on one primary tool but create bounded exception lanes for named populations.
        decision-domain: operating_model
        position: viable
      - path: decision/operating-model/single-standard
        title: Single standard tool
        summary: Move all developer populations onto one approved tool unless a later constraint proves that unworkable.
        decision-domain: operating_model
        position: deferred
  resolutions:
    - when-facts-all: [operating_model=single_standard]
      decision: "The target operating model is one standard harness for the default developer population."
    - when-facts-all: [operating_model=multi_harness_governed]
      decision: "The target operating model is a governed multi-harness portfolio under one shared control model."
    - when-facts-all: [operating_model=default_plus_exceptions]
      decision: "The target operating model is one default harness with formal exception lanes for named populations."
---

When the enterprise already has more than one coding tool in flight, the first
decision is not "which single harness wins?" It is **what operating model will
govern tool choice**. Without that decision, the platform drifts into unmanaged
tool sprawl: inconsistent controls, overlapping spend, and architecture debates
that confuse current-state evidence with target-state design.

## Target-State Operating Models

| Operating model | What it means | When it fits | Main risk |
|---|---|---|---|
| Single standard harness | One approved tool for nearly everyone | Strong standardization mandate; limited persona variance | Lowest flexibility; exception pressure rises quickly |
| Governed multi-harness portfolio | Several approved tools under one control plane | Distinct developer populations or workflow shapes need different tools | Governance complexity if controls are not truly shared |
| Default + exceptions | One default tool, plus bounded approved exceptions | Org wants standardization with a narrow escape hatch | Exceptions become shadow standards if not reviewed |

Do not let the advisor collapse these into one question about vendor preference.
This is an operating-model decision first, a product-selection decision second.

## Decisions

**Which developer populations map to which harnesses?**
- Define the primary populations explicitly: general application developers,
  platform engineers, data scientists, regulated-repo contributors, high-autonomy
  CI/CD users, contractors
- For each population, state:
  - default harness
  - allowed alternative harnesses
  - disallowed harnesses
  - reason the mapping exists

**What governance must be shared across all approved harnesses?**
- SSO / enforced corporate identity
- approved model-routing path and provider policy
- MCP / tool catalog policy
- logging and audit export
- quota and spend controls
- data handling and retention posture
- exception approval and revocation workflow

If those controls are not shared, the portfolio is not governed; it is just a
collection of tools.

**Is there a default harness?**
- Yes: define the default and its success criteria
- No: define the routing logic by persona, repo class, or workflow

**How are exceptions approved?**
- Named populations only
- time-bounded exceptions with renewal
- repo- or environment-scoped exceptions
- no permanent personal exceptions without review

**When do you add a custom enterprise harness lane?**
- Add one only when the portfolio needs a central capability the vendor tools
  cannot provide consistently:
  - durable/background agents
  - central execution for sensitive repos
  - custom approval logic
  - shared enterprise-only orchestration
  - uniform behavior across tool surfaces

The custom lane is usually an addition to the portfolio, not a replacement for
interactive IDE-native tools.

## Reference Pattern

```
Developers
├── Default lane: Copilot or Claude Code for general IDE workflows
├── Specialized lane: Cursor for high-velocity single-file editing populations
├── OpenAI/Codex lane: approved where OpenAI ecosystem integration is required
└── Enterprise custom lane: central background agents / CI automation only

Shared governance plane
├── Corporate IdP + group mapping
├── Approved model routing policy
├── Shared MCP / tool gateway policy
├── Central logging + cost attribution
├── Guardrails / DLP / quota policy
└── Exception registry + review workflow
```

## Principles

- Govern the portfolio, not each tool in isolation
- Population-to-harness mapping must be explicit and reviewable
- Exception paths must expire unless re-justified
- Shared control points matter more than perfect tool uniformity
- A custom harness is justified by missing control or capability, not by the
  mere existence of multiple approved vendor tools

## Connects to

- [SaaS Coding Agent Products](saas-products.md) — use this after the operating
  model is clear to decide which products belong in the approved portfolio
- [Harness Lifecycle Implications](lifecycle-implications.md) — portfolio design
  changes which downstream decisions are shared versus tool-specific
- [Policy Tiers](../access/policy-tiers.md) — the mechanism for population-based
  differentiation and time-bounded exceptions
- [Quota & Rate Limits](../access/quota.md) — enforce spend boundaries across all
  approved harnesses
- [Identity & Access](../access/identity.md) — SSO and group mapping must be
  consistent across the portfolio
- [MCP Gateway](../gateway/mcpgw.md) — shared tool-governance layer across
  different harnesses
- [Model Gateway](../gateway/modelgw.md) — keep provider and model policy
  consistent even when harnesses differ
- [Observability & Audit](../ops/observability.md) — central audit trail is what
  makes the portfolio governable
