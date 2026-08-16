---
type: platform-component
title: Security Operations
description: incident response patterns specific to coding agent platforms
group: access
tags: [access, security, incident-response, secops, mcp-compromise, credential-leak]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [incident-response, secops, mcp-compromise, credential-leak, security-monitoring, compromise]
decision-question: "How will you detect and respond to security incidents specific to coding agents — compromised MCP servers, credential leaks, and prompt injection attacks in production?"
---

The [Security Posture](security-posture.md) node maps the threat surface and
preventive controls. This node covers the operational side: detection signals,
incident response runbooks, and recovery patterns specific to coding agent
platforms. These are different from traditional AppSec incidents because the
agent is an active participant in the incident — it may be the vector or the victim.

## Incident Types and Response Patterns

### Compromised or malicious MCP server

**Detection signals:**
- Unusual outbound data volume from the MCP gateway to a specific target
- Tool call patterns inconsistent with the task context (e.g., exfiltration calls
  during a code review session)
- Developer reports unexpected agent behavior traced to a specific MCP server
- New MCP server deployed outside normal registry approval process

**Immediate response:**
1. Disable the MCP server at the registry level — remove from allowlist;
   all sessions immediately lose access to that server's tools
2. Revoke the server's credentials at the MCP gateway — server-side credential
   injection means there is a single revocation point
3. Audit all sessions that invoked that server within the incident window —
   [Observability](../ops/observability.md) audit trail is the source of truth
4. Review the approval chain: who approved this server, when, under what review

**Recovery:**
- Do not re-enable without a clean forensic review of the server's source code
  and a new provenance check
- If the server was a third-party package: pin to the last-known-good version
  or fork under internal governance

---

### Credential leak via tool call

**Scenario:** An agent calls a tool that includes a credential in its parameters
or response, and that credential appears in session logs or is exfiltrated.

**Detection signals:**
- Secret scanner alert on audit log content (integrate with tools like truffleHog
  or similar against the audit trail)
- Unusual authentication attempts against internal systems using a service
  credential that should only be used by the MCP gateway

**Immediate response:**
1. Rotate the credential immediately — do not wait for root cause analysis
2. Review all audit logs for uses of that credential in the incident window
3. Identify the tool or MCP server that exposed the credential and disable it
4. Check whether the credential was server-side injected (should be) or passed
   as a call parameter (should not be) — if the latter, this is a design violation
   to fix before re-enabling

**Prevention going forward:**
- Secret scanning on all outbound tool call parameters and responses at the
  MCP gateway level — not just on audit log ingestion
- Enforce credential injection posture: credentials live in the gateway, never
  in call parameters; audit any MCP server implementation that asks for a
  credential as a parameter

---

### Prompt injection incident in production

**Scenario:** An agent processing a retrieved file, web page, or tool response
follows embedded instructions from that content rather than the developer's
legitimate task.

**Detection signals:**
- Agent takes actions inconsistent with the developer's stated task
- Agent calls tools the developer did not direct (especially write or destructive tools)
- Developer reports the agent "did something unexpected" after processing external content
- Guardrail firing on an output type not expected for the current task context

**Immediate response:**
1. Terminate the affected session immediately
2. Review the session trace to identify the injection vector (which tool response,
   file, or URL contained the malicious instruction)
3. If a write or destructive action was already taken: trigger rollback procedures
   per [Rollback & Change Safety](../harness/rollback.md)
4. Block the injection source: if a URL or external domain, add to deny-list;
   if an internal file, flag for security review

**Systemic response:**
- Review guardrail configuration — did the guardrail miss a write action initiated
  by injected instructions? If yes, update the rule to require approval for
  tool calls not traceable to the original task intent
- Consider requiring human approval for any write or destructive tool call when
  the preceding context includes externally retrieved content

---

### Unusual developer or agent behavior patterns

**Scenarios:** A developer's agent is making calls inconsistent with their tier
(excessive tool calls, access to systems outside their team's scope); or a
pattern suggests a developer account has been compromised.

**Detection signals:**
- Developer's session usage suddenly spikes far above historical patterns
- Tool calls targeting systems outside the developer's normal workspace
- Calls to high-sensitivity tools (data store writes, production systems) that
  are inconsistent with the developer's tier or role
- Multiple sessions from unusual geographic locations or times

**Response:**
1. Flag for review via the progressive-trust negative-signal pipeline
2. If active suspicious session: terminate the session; notify the developer and
   their manager
3. If account compromise suspected: suspend agent access pending IdP credential
   review; coordinate with IT security for full account investigation

## Security Monitoring Configuration

**Alerts to configure from day one:**

| Signal | Threshold | Action |
|---|---|---|
| MCP server calling undeclared endpoints | Any | Page on-call; disable server |
| Credential pattern in tool call parameter or response | Any | Immediate alert; rotate |
| Guardrail firing rate spike | > 3× baseline in 15 min | Investigate source |
| Session cost anomaly | > 5× developer's 7-day average | Flag for review |
| New MCP server deployed outside registry | Any | Alert platform team |
| Tool calls to production write systems outside approved tier | Any | Terminate session; page |

## Stack Options

**Security monitoring and alerting**
- Amazon GuardDuty — threat detection for unusual API call patterns, credential
  anomalies, and data exfiltration signals from CloudTrail and VPC flow logs;
  no agent-specific config required; catches credential misuse at the AWS layer
- Amazon Security Hub — aggregates findings from GuardDuty, Macie, and Inspector;
  single pane for triage; integrates with SIEM via EventBridge
- Amazon Macie — PII and sensitive data detection in S3; if audit logs or
  session exports land in S3, Macie catches credential or PII exposure in those
  files before they are read by other systems
- Amazon Detective — investigation and root-cause analysis across GuardDuty
  findings; useful for tracing the blast radius of a compromised MCP server
- AWS CloudTrail — all AWS API calls logged; the primary evidence trail for any
  incident involving AWS-hosted MCP servers, AgentCore endpoints, or IAM credential use

**Secret scanning on audit logs**
- truffleHog / gitleaks — run as a Lambda triggered on audit log S3 PutObject;
  catches credential patterns before they are retained long-term
- AWS Macie custom data identifier — define patterns matching your credential
  format (e.g., API key prefix patterns); Macie flags matches in S3 continuously

**MCP server kill switch**
- AgentCore Gateway allowlist API — single API call to remove a server from the
  allowlist; takes effect on the next tool dispatch; no session restart required
- AWS Systems Manager Parameter Store / Secrets Manager — revoke the MCP server's
  credential at the source; the gateway's next credential injection request gets
  a revoked or missing secret, which fails the call cleanly

**Incident response automation**
- AWS EventBridge + Lambda — trigger an automated response (disable MCP server,
  rotate secret, page on-call) on a GuardDuty finding or CloudWatch alarm
- AWS Incident Manager — structured runbooks, escalation paths, and post-incident
  analysis for declared incidents; integrates with PagerDuty and Slack

**Session termination**
- AgentCore Runtime API — terminate an active agent session programmatically;
  needed for incident response when a session needs to be stopped mid-execution
- AWS Lambda + API Gateway — if using a self-managed harness, expose a
  session-terminate endpoint callable by the incident response automation

## Principles

- The agent is an active participant in incidents — unlike a passive data store,
  a compromised agent actively executes actions; response time measured in minutes
  matters more than in traditional data breach scenarios
- Single revocation points matter: server-side credential injection and the MCP
  gateway allowlist exist precisely so that incident response is a single-action
  operation (disable the server, rotate the credential) rather than hunting
  through dozens of client-side credential stores
- Every incident response action must itself be logged — the audit trail for
  the incident response is as important as the audit trail for the incident
- Post-incident: update the threat model and security posture accordingly;
  a prompt injection incident that exploited a missing guardrail rule is evidence
  to add that rule, not just to patch the specific session

## Connects to

- [Security Posture](security-posture.md) — preventive controls; this node
  covers operational response after prevention fails
- [Observability & Audit](../ops/observability.md) — the audit trail is the
  primary evidence source for every incident type; it must be tamper-evident
  and queryable under time pressure
- [MCP Gateway](../gateway/mcpgw.md) — credential revocation and allowlist
  management are gateway operations; the gateway is the primary response surface
- [Registry / Catalog](../registry/registry.md) — MCP server disable/remove is
  a registry operation; the allowlist is the kill switch
- [Rollback & Change Safety](../harness/rollback.md) — write/destructive actions
  from a compromised session need rollback; the rollback mechanism must be
  accessible to the incident responder, not just the developer
- [Progressive Trust](progressive-trust.md) — anomalous behavior patterns are
  the negative signals that drive tier downgrade in the progressive trust model
