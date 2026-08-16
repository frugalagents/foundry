---
type: platform-component
title: Identity & Access
description: SSO · AuthN/Z · entitlements
group: access
tags: [access, governance, identity]
timestamp: 2026-08-12T00:00:00Z
status: stable
traversal: mandate
decision-question: "How will your identity provider authenticate developers and govern which agent identities can reach which tools?"
---

Federates to your corporate identity provider and authenticates every request
before it reaches the harness — and it governs egress too: which identity may
reach which enterprise tool or dataset through the MCP Gateway. One access
model covers both ingress (who can talk to the agent) and tool egress (what
the agent can reach on their behalf).

Agent identities are commonly implemented as workload identities — a
specialized identity type distinct from human user identities, carrying
attributes (session scope, delegation chain) that let a platform tell "this
call is the agent acting for user X" apart from "this call is user X directly."

## Decisions

**Identity source?**
- Corporate IdP (Okta / Entra / Cognito) via OIDC/SAML — reuse existing
  enterprise auth, no new account system
- SCIM auto-provisioning of teams — access follows org-chart changes
  automatically, more setup cost up front (standard IdP capability, not
  yet verified against a coding-agent-specific source — see `## Sources`)

**Agent acts as whom?**
- The developer — inherits their access; simplest mental model, but the agent
  can now reach everything the developer can, even for read-only tasks
- Scoped service identity — least privilege; requires maintaining a separate
  entitlement mapping from developer to agent scope

**Tool-access model?**
- Role → allowed tools/datasets — coarse-grained, easy to reason about at scale
- Per-agent grants — explicit, but doesn't scale past a handful of agents
- Env-scoped — dev vs. prod tools differ; needed once agents can reach
  production systems at all

## Principles

- Federate — no local accounts to provision, rotate, or leak
- Same identity model governs ingress AND tool egress; don't split them into
  two systems that can drift out of sync
- Short-lived, scoped tokens — never long-lived static credentials for an
  agent identity

## Stack Options

**Scoped service identity**
- AWS Bedrock AgentCore Identity — implements agent identities as first-class
  workload identities (distinct attributes from human users: session scope,
  delegation chain), with native outbound credential brokering to third-party
  services. Fits when the rest of the stack is already AgentCore-based.

**The developer (inherits their access)**
- Claude Code (local mode) — code execution and file access stay local under
  the invoking developer's own session; no separate scoped-credential layer
  is interposed the way Claude Code's own cloud execution mode explicitly
  adds one. Choosing this option is often "keep the local default" rather
  than adding a broker.

## Connects to

- Entitles every call through the [MCP Gateway](../gateway/mcpgw.md)
- Governed by the same identity source as [Guardrails & Policy](guardrails.md)
  and [Quota & Rate Limits](quota.md)

## Sources

- [AgentCore Identity: Provide identity management for agent applications](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.md) — checked 2026-08-12 — supports: agent identities as workload identities distinct from human identities, native integration with an agent runtime and gateway for both inbound auth and outbound credential brokering
- [Manage credential providers with AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-outbound-credential-provider.md) — checked 2026-08-12 — supports: credential management across multiple trust domains as a distinct concern from inbound authentication
- [Claude Code — Security](https://code.claude.com/docs/en/security) — checked 2026-08-13 — supports: local execution keeping code/file access under the developer's own session with no scoped-credential broker layer, contrasted explicitly against cloud execution mode's secure proxy + scoped credential translation
