---
type: advisory-decision-slice
title: Shared Model Routing Boundary
description: force an explicit decision on whether providers and tiers are governed centrally or left to each harness
group: decision-slices
tags: [decision-slice, model-routing, gateway, provider-policy]
timestamp: 2026-08-25T00:00:00Z
status: candidate
traversal: conditional
decision-question: "Will approved harnesses share one model gateway with provider and tier policy, or will each tool manage provider credentials and model choice independently?"
decision-domain: model_routing
priority: 8
requires: [gateway/modelgw, gateway/model-tiering, access/quota]
advisory:
  slice: true
  fact-rules:
    - key: multiple_model_providers
      value: true
      match-any: [multi-provider, multiple providers, provider fallback, cross-provider]
      fact-text: "More than one model provider appears to be in scope."
    - key: multiple_model_providers
      value: true
      match-all: [bedrock, openai]
      fact-text: "More than one model provider appears to be in scope."
    - key: multiple_model_providers
      value: true
      match-all: [bedrock, anthropic]
      fact-text: "More than one model provider appears to be in scope."
    - key: multiple_model_providers
      value: true
      match-all: [azure openai, bedrock]
      fact-text: "More than one model provider appears to be in scope."
    - key: multiple_model_providers
      value: true
      match-all: [vertex ai, bedrock]
      fact-text: "More than one model provider appears to be in scope."
    - key: model_gateway
      value: shared
      match-any: [model gateway, shared model gateway, central model gateway, one inference gateway, shared inference endpoint, common model route, common gateway]
      fact-text: "The target state appears to use one shared model routing boundary."
    - key: model_tiering
      value: tiered
      match-any: [tiered routing, tiered model strategy, cheaper model for simple tasks, frontier for complex tasks, route by complexity, haiku for simple, sonnet for editing, frontier models for architecture]
      fact-text: "The target state appears to use explicit model tiering by task shape."
    - key: provider_credentials_per_tool
      value: true
      match-any: [tool-specific credentials, each tool has its own api key, direct openai api keys, direct provider keys, separate provider credentials]
      fact-text: "At least one harness is being allowed to manage provider credentials outside a shared gateway."
  activate:
    requires-facts-all: [shared_control_plane]
    requires-facts-any: [multiple_model_providers, provider_credentials_per_tool, model_tiering]
  output:
    decision-focus: model_routing
    question:
      id: model-routing-shared-gateway
      text: "Will all approved harnesses route models through one shared gateway with provider and tier policy, or will each tool manage provider credentials and model choice independently?"
      why-it-matters: "If model routing is left to each harness, cost, resilience, and compliance policy fragment even when the rest of the control plane looks shared."
      decision-domain: model_routing
    recommendation: "Keep provider access and model tiering behind one shared gateway. Challenge any plan where each harness carries separate provider keys or picks models independently."
    risks:
      - "Per-tool provider credentials will fragment cost control, resilience policy, and auditability even if the surface and identity layers look standardized."
    options:
      - path: decision/model-routing/shared-gateway-tiered
        title: Shared gateway with model tiering
        summary: Route all approved harness traffic through one gateway with explicit provider and complexity-tier policy.
        decision-domain: model_routing
        position: recommended
      - path: decision/model-routing/shared-gateway-frontier-default
        title: Shared gateway frontier default
        summary: Keep one shared model gateway but defer tiering and route most work to one stronger default model class.
        decision-domain: model_routing
        position: viable
      - path: decision/model-routing/per-tool-provider-config
        title: Per-tool provider configuration
        summary: Let each harness manage its own provider credentials and model-selection logic.
        decision-domain: model_routing
        position: deferred
  resolutions:
    - when-facts-all: [multiple_model_providers, model_gateway=shared, model_tiering=tiered]
      decision: "Approved harnesses route model calls through one shared gateway with explicit provider and tiering policy rather than per-tool credentials."
---

This slice exists because provider sprawl often reappears one layer below the
harness discussion. Even if the enterprise agrees on shared identity and audit,
the platform still fragments if each tool manages provider credentials, fallback,
and tiering independently.

## Connects to

- [Model Gateway](../gateway/modelgw.md)
- [Model Tiering](../gateway/model-tiering.md)
- [Quota & Rate Limits](../access/quota.md)
