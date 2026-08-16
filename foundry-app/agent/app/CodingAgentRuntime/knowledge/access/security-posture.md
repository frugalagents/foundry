---
type: platform-component
title: Security Posture
description: attack surface taxonomy — prompt injection, excessive agency, MCP-specific threats
group: access
tags: [access, security, owasp, mcp-security, threat-model]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: mandate
decision-question: "What is the full attack surface of your coding agent platform, and which controls are required vs. recommended?"
---

A coding agent platform has a materially different attack surface than a
traditional web application. Security posture must be scoped at architecture
time — not as a post-blueprint review item. This node enumerates the key threat
categories and maps them to platform controls.

## Threat Categories

### Prompt injection (OWASP LLM01)
Malicious content in a retrieved file, tool response, or external web page
overrides the agent's intended behaviour. An adversarially crafted comment
in a dependency, a poisoned Jira ticket, or a tool response containing
instruction text can all redirect the agent.

**Controls:** Input scanning in [Guardrails & Policy](guardrails.md); restrict
[Web & Search](../external/web.md) access to approved sources; require developer
approval before high-risk destructive actions; scoped tool permissions in
[Permission Engine](../harness/perms.md).

### Excessive agency (OWASP LLM08)
The agent is given more permissions or a broader tool set than its tasks require.
A developer-scoped agent that can also push to production branches is excessive.

**Controls:** Least-privilege [scoped service identity](identity.md); per-tool
allow/deny in [Permission Engine](../harness/perms.md); require-approval mode
for any write or destructive action outside the current task scope.

### Supply chain compromise (OWASP LLM03 / LLM05)
A malicious or tampered MCP server, tool binary, or skill package injected into
the platform registry. A compromised MCP server can exfiltrate code or credentials
through ostensibly normal tool calls.

**Controls:** [Provenance](../registry/provenance.md) — signing and verification
before registry admission; [Registry / Catalog](../registry/registry.md) —
allowlist-only model, no unreviewed servers reach developers; operator review
gate before any new MCP server goes live.

### Insecure plugin design (OWASP LLM07)
An MCP server or tool exposes more capability than intended, or passes raw
credentials in call parameters where they can be logged or intercepted.

**Controls:** [MCP Gateway](../gateway/mcpgw.md) credential injection — credentials
are injected server-side, never passed as call parameters; scope minimisation in
MCP server design — each server exposes the minimum required surface.

### MCP-specific: confused deputy
The agent calls a tool on behalf of one user but the tool executes with broader
permissions than that user should have — because the tool's ambient credentials
exceed what the calling user is entitled to.

**Controls:** [AgentCore Identity](identity.md) workload identities carry delegation-
chain attributes so the tool boundary can verify "this call is agent acting for
user X with scope Y"; MCP Gateway enforces per-caller scope at the tool boundary.

### MCP-specific: SSRF via tool
A tool accepts a URL parameter and an agent-supplied (or attacker-supplied) URL
targets an internal service, cloud metadata endpoint, or other sensitive network
resource.

**Controls:** URL allowlisting in tool implementation; MCP Gateway request
inspection for SSRF patterns; disable URL-accepting tools for agents that don't
need external network access.

### MCP-specific: local server compromise
A local MCP server process running on the developer's machine is a privilege
escalation surface — a compromised local server process runs with the developer's
OS permissions.

**Controls:** Prefer managed MCP over local-process-per-developer; where local
servers are required, run them at minimum required OS privilege; include local
MCP servers in the provenance and review process, not just remote ones.

## Decisions

**Security review scope?**
- Model boundary only — misses tool and supply-chain risk; not sufficient for
  any regulated or production-facing deployment
- Full attack surface (model + tools + MCP servers + code execution + data retrieval)
  — required for regulated environments, for any agent with write access to
  production systems, and for multi-tenant platforms

**Who owns the security posture?**
- Platform team (centrally enforced) — consistent; developers cannot opt out of
  baseline controls
- Team-by-team — faster initial rollout; risk of inconsistent controls and
  unreviewed MCP server deployment

**Minimum required posture for regulated environments:**
- Complete audit trail: every agent action logged with actor, timestamp, scope,
  content hash; see [Observability & Audit](../ops/observability.md)
- No external web access without explicit per-session approval
- MCP server allowlist: no unreviewed server reaches a developer
- Scoped service identity — not "acts as the developer" with their full access
- Input scanning for prompt injection on all external data sources

## Stack Options

**Prompt injection defense**
- Claude Code guardrails (managed) — operator-configured input/output filters;
  applied to all sessions centrally; no custom code required
- Amazon Bedrock Guardrails — managed; configurable content filters, denied
  topics, and PII masking applied at the API layer before the model sees input;
  also blocks outputs; works with any Bedrock-hosted model
- Custom pre-processor Lambda — inspect tool responses and retrieved content
  for injection patterns before they enter the agent's context; useful for
  patterns Bedrock Guardrails doesn't cover (e.g., code-comment injection)

**Excessive agency / permission control**
- AgentCore Identity + scoped workload identities — each agent session carries
  only the permissions declared at workload identity creation; exceeding scope
  fails at the IAM/gateway layer, not just at the guardrail
- Claude Code permission engine (admin-managed) — allow/deny tool lists set
  centrally; developers cannot override the platform-admin-set deny list
- AWS IAM permission boundaries — set a maximum permission boundary on the
  agent's IAM role; even if the role tries to assume broader permissions, the
  boundary caps what it can actually do

**Supply chain / provenance**
- AWS CodeArtifact — private package repository; pin MCP server dependencies
  to internal-mirrored packages with integrity checks; no direct PyPI/npm pull
- AWS Signer — code signing for Lambda functions and container images used as
  MCP servers or harness code; enforces that only signed artifacts can be deployed
- Amazon Inspector — continuous vulnerability scanning of container images and
  Lambda functions; flags known CVEs in MCP server or harness dependencies

**Secret scanning**
- Amazon Macie — PII and credential detection in S3; covers audit log exports
  and session transcripts stored in S3
- AWS Secrets Manager rotation — automatic rotation of credentials used by the
  MCP gateway; reduces the window of exposure from a leaked credential
- truffleHog / detect-secrets (OS) — run in CI on MCP server code repositories;
  prevents secrets being committed to the MCP server codebase

**MCP-specific: SSRF protection**
- VPC endpoint policies — restrict which AWS services the agent's VPC can call;
  prevent SSRF from reaching AWS metadata endpoints (169.254.169.254)
- AWS WAF — if any agent-accessible tool has a web-facing endpoint, WAF rules
  can block SSRF probe patterns
- URL allowlist enforcement in tool code — Lambda-based tools validate URL
  parameters against an allowlist stored in Parameter Store before making
  outbound calls

## Principles

- Security posture is a first-class architecture decision, not a post-deployment
  checklist — resolve it before the blueprint is finalised
- The same identity model governing inbound auth must also govern outbound tool
  access; two separate systems that can drift out of sync are a security gap
- Prompt injection is the highest-probability threat for any agent that reads
  external files, web pages, or third-party tool responses — treat external data
  as untrusted input, not trusted context

## Connects to

- [Guardrails & Policy](guardrails.md) — input/output filtering enforcement
- [Permission Engine](../harness/perms.md) — per-tool allow/deny at runtime
- [Provenance](../registry/provenance.md) — supply-chain controls for tools and
  MCP servers
- [Identity & Access](identity.md) — scoped service identity and delegation chain
- [MCP Gateway](../gateway/mcpgw.md) — credential injection and SSRF inspection

## Sources

- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) — checked 2026-08-12 — confused deputy, SSRF via URL parameters, local server compromise, scope minimisation
- [OWASP GenAI / LLM Top 10 v2025](https://genai.owasp.org/llm-top-10/) — checked 2026-08-12 — LLM01 prompt injection, LLM03 supply chain, LLM05 improper output handling, LLM07 insecure plugin design, LLM08 excessive agency
