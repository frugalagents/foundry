---
type: platform-component
title: Managed Agent Runtime
description: custom agent code on managed infra — Bedrock AgentCore and equivalents
group: harness-selection
tags: [harness-selection, managed-runtime, agentcore, aws]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [managed-runtime, agentcore, custom-harness-on-managed-infra, aws-native]
decision-question: "Do you want custom agent logic with vendor-managed execution infrastructure, scaling, and security isolation?"
decision-domain: harness_family
priority: 9
blocking: true
alternatives: [harness-selection/saas-products, harness-selection/coding-harnesses, harness-selection/oss-frameworks]
implies: [gateway/mcpgw, gateway/modelgw, access/identity]
---

A managed runtime gives you a custom agent codebase on fully managed infrastructure.
Your code drives the agent loop and tool dispatch; the vendor handles compute
orchestration, per-session isolation, scaling, and observability plumbing.

AWS Bedrock AgentCore is the primary example: it hosts agent logic in a managed
container runtime, provides microVM-level per-session isolation, native memory and
gateway integration, and IAM-backed identity — without you running any of that infra.

## Decisions

**How deeply do you adopt the managed stack?**
- Full stack: Runtime + Memory + Gateway + Identity together; strongest integration,
  most opinionated, fastest to operational
- Selective: use only the runtime (custom MCP servers elsewhere) or only the gateway
  (self-managed agent code calling AgentCore Gateway for tool routing)
- Mix-and-match: AgentCore runtime + external observability (e.g., Datadog instead
  of CloudWatch) — valid, review the integration points

**How is agent code deployed?**
- Container image pushed to the runtime endpoint; versioned deployments with
  canary/blue-green support
- Endpoint per agent version — traffic can be split across versions during rollout

**State and session management?**
- AgentCore Memory: native structured memory with extraction jobs for pattern mining
- External store: needed if your memory model doesn't fit AgentCore's primitives

## Stack Options

**Full AgentCore stack (AWS managed)**
- AgentCore Runtime — deploy agent code as a container image; versioned
  endpoints; canary deployment support; microVM isolation per session native;
  no cluster management
- AgentCore Memory — structured memory store with extraction jobs; queryable
  by agents at session start; integrates with the runtime without extra glue
- AgentCore Gateway — managed MCP gateway; add targets via API; credential
  injection via IAM or stored API key; allowlist enforcement built in
- AgentCore Identity — workload identities with delegation-chain attributes;
  IAM-integrated; outbound credential brokering to third-party services
- CloudWatch — native observability destination; session traces, events, and
  errors; set log retention and metric alarms; export to SIEM via Firehose

**Selective adoption**
- AgentCore Runtime only + self-managed MCP servers — use the managed runtime
  for agent code execution and isolation; bring your own MCP server instances;
  connect them to the runtime via the standard MCP protocol
- AgentCore Gateway only + self-managed agent code on ECS — use the gateway
  for credential injection and tool routing; run your own agent loop on ECS;
  useful when you have existing agent code not ready to containerise for the
  runtime
- AgentCore Memory only — use the memory store as a standalone cross-session
  state backend for an OSS-framework harness; avoids building your own memory
  persistence layer

**When NOT to use AgentCore**
- Air-gapped or non-AWS environments — AgentCore is an AWS managed service;
  not available on-prem; use an OSS framework in those cases
- FedRAMP High boundary — verify AgentCore's current authorization status;
  if not yet in the boundary, use self-hosted OSS on AWS GovCloud instead

## Principles

- Managed runtime = your business logic, vendor's infra operations — you own agent
  behaviour and quality; the vendor owns uptime, scaling, and isolation boundaries
- Identity for outbound tool calls is injected by AgentCore Identity, never passed
  as raw credentials in call parameters — same credential-brokering posture as the
  MCP Gateway; verify this posture is maintained in your agent code too
- Observability is native to CloudWatch — review log retention and export settings
  against your audit trail requirements before go-live; default retention may be
  shorter than compliance requires

## Connects to

- [Execution — microVM](../exec/microvm.md) — native per-session isolation boundary
  in AgentCore
- [MCP Gateway](../gateway/mcpgw.md) — AgentCore Gateway handles tool call routing
  when adopted
- [Identity & Access](../access/identity.md) — AgentCore Identity implements workload
  identities with delegation chain attributes
- [Observability & Audit](../ops/observability.md) — traces and events exported to
  CloudWatch; review retention and export for compliance requirements
- [Lifecycle Implications](lifecycle-implications.md) — what this choice pre-resolves

## Sources

- [AgentCore Runtime guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html) — to verify on first use
- [AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html) — checked 2026-08-12
- [AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html) — to verify on first use
