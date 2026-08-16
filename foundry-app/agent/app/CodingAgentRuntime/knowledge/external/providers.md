---
type: platform-component
title: Model Providers
description: frontier · self-hosted LLMs
group: external
tags: [external, models, residency]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: mandate
decision-question: "Which model provider(s) will serve inference, and what are your data-residency, compliance, and access constraints?"
---

The model providers that actually serve inference — frontier APIs or
self-hosted models — reached exclusively through the
[Model Gateway](../gateway/modelgw.md). This component is the destination
the model gateway routes to; data residency and network placement are
properties of *this* component, not of the gateway itself.

## Decisions

**Hosting?**
- Managed provider (e.g. a cloud model API) — least operational burden,
  depends on the provider's own residency/compliance posture
- Self-hosted — needed for sensitive or air-gapped workloads a managed
  provider's standard offering can't satisfy
- Multi-provider — for resilience, ties directly to
  [Model Gateway](../gateway/modelgw.md)'s multi-provider-with-fallback
  decision

**Network placement?**
- Public — simplest, inference reachable over the public internet (still
  authenticated/encrypted, but not network-isolated)
- VPC-connected — the runtime/tooling connects into a private network via
  managed network interfaces, with no internet access by default unless a
  NAT gateway is explicitly configured; this is a deployment-time network
  mode choice (e.g. `networkMode: PUBLIC | VPC`), not something implied by
  any other component's egress-allowlist setting
- On-prem / air-gapped — the strongest residency posture, at the cost of
  running and maintaining the inference infrastructure entirely yourself

**Residency granularity, if VPC-connected?**
- Region-pinned inference — constrains which region serves requests,
  without necessarily isolating network reachability
- Private subnets with no direct internet route — the strongest posture;
  outbound internet access (if needed at all, e.g. for a tool that must
  reach the public web) requires an explicit NAT gateway and route table
  configuration, not an assumption of connectivity

## Principles

- Pin model versions and test before rollout — an unpinned model reference
  can change behavior underneath you without any code change on your side
- Route residency-sensitive traffic to compliant regions/network
  configurations deliberately — this is a placement decision made once at
  deployment time, not something to leave implicit in whatever the default
  happens to be
- VPC connectivity is a distinct decision from the egress-allowlisting a
  sandboxing component might apply — network *placement* (can this even be
  reached, and from where) and *content* filtering on a network call are
  two different layers, and a platform serving regulated data needs both
  addressed, not just one

## Connects to

- Reached exclusively through the [Model Gateway](../gateway/modelgw.md) —
  never a direct binding from the harness to a specific provider
- Network placement here should be reconciled with whichever
  [sandboxing component](../exec/index.md)'s egress posture the platform
  runs code under — a regulated deployment likely wants both constrained

## Sources

- [Configure AgentCore Runtime and built-in tools VPC configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.md) — checked 2026-08-12 — supports: an explicit `networkMode: PUBLIC | VPC` deployment configuration as a distinct decision from tool-level egress settings, no internet access by default when VPC-connected (requiring an explicit NAT gateway + route table to enable it), and private-subnet placement as the mechanism for residency-sensitive network isolation
