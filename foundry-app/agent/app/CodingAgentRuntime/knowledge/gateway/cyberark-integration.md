---
type: platform-component
title: CyberArk PAM Integration
description: integrating CyberArk Privileged Access Management as the credential source for MCP gateway tool call injection — CCP API adapter, ephemeral credential handling, and PAM workflow integration for enterprises where CyberArk is the enterprise PAM standard
group: gateway
tags: [gateway, cyberark, pam, privileged-access, ccp, ccp-api, credential-injection, ephemeral-credentials, financial-services]
timestamp: 2026-08-15T00:00:00Z
status: candidate
traversal: conditional
trigger: [cyberark, pam, privileged-access-management, ccp-api, cyberark-vault, enterprise-pam, no-secrets-manager, credential-checkout, password-vault]
decision-question: "Is CyberArk (or an equivalent enterprise PAM system — BeyondTrust, Delinea) your enterprise standard for privileged credential management, meaning the MCP gateway cannot inject credentials from AWS Secrets Manager or HashiCorp Vault alone, and must integrate with the PAM system's API to check out credentials at session time?"
decision-domain: secrets_integration
priority: 7
requires: [gateway/mcpgw]
alternatives: [gateway/vault-integration]
---

CyberArk is the dominant enterprise PAM (Privileged Access Management) platform
at large financial institutions, regulated enterprises, and government contractors.
It provides a Central Credential Provider (CCP) — a REST API that applications
use to check out credentials from the CyberArk Vault at runtime, without the
application ever storing credentials.

The standard MCP gateway credential injection (Secrets Manager or HashiCorp Vault)
does not integrate with CyberArk. Enterprises where CyberArk is the PAM standard
require a CyberArk-specific credential broker that:
- Authenticates to the CCP using a platform-specific application identity
- Checks out the required credential at session start
- Injects it into the MCP tool context (in-memory only)
- Returns the credential to CyberArk (check-in) at session end
- Produces an audit event that correlates with the CyberArk access audit trail

This is a 1-2 sprint build. The CyberArk CCP is well-documented and REST-based.
The primary design challenges are: application identity registration with the
CyberArk team (a governance process, not a coding problem), and credential
check-in reliability on session end (the platform must not leave credentials
checked out permanently if a session ends abnormally).

## How CyberArk CCP Credential Injection Works

```
Session init
  └── Lambda authorizer
        ├── Authenticate developer (Okta → IAM Identity Center)
        └── cyberark-credential-broker Lambda
              ├── Authenticate to CCP (AppID + client certificate)
              ├── Request credential by Safe + Object name
              │     └── CyberArk Vault: check out credential
              ├── Inject into MCP tool context (in-memory)
              └── Register check-in callback (session end hook)

Session active
  └── MCP gateway tool call
        └── Tool receives injected credential from session context

Session end (normal or timeout)
  └── cyberark-credential-broker Lambda (check-in invocation)
        ├── POST /AIMWebService/api/Accounts/{accountID}/Credentials/Retrieve
        │     (check-in via account reconcile or explicit return)
        └── Log session_id → CyberArk account access event correlation
```

## Decisions

**Which CyberArk CCP authentication method does the adapter use?**
- Certificate-based authentication (recommended) — the adapter Lambda holds a
  client certificate issued by the organization's PKI; the certificate's Common
  Name matches the registered CyberArk Application ID; the CCP validates the
  certificate at each request; certificates are stored in ACM Private CA and
  mounted into the Lambda via Secrets Manager (the certificate, not the private
  key, is not sensitive; only the private key must be protected); rotation via
  ACM automation
- OS-credential authentication (IIS/Windows only) — not applicable to Lambda-based
  adapters; CyberArk-specific to Windows IIS deployments
- Allowed machines / IP restriction — the CyberArk Application ID is registered
  with an allowed-machines list that includes the Lambda's NAT gateway IP; requests
  from other IPs are rejected by CCP; used as a defense-in-depth control alongside
  certificate authentication; requires a stable NAT gateway IP (Elastic IP) for
  the Lambda's VPC

**How is the CyberArk Application ID registered and managed?**
- PAM team registers the application — the platform team submits a CyberArk
  application registration request to the PAM team specifying: Application ID name,
  allowed machines (NAT gateway EIP), authentication method (certificate), and
  the Safes the application needs access to; this is a governance step, not a
  code step; factor in 1-2 weeks for PAM team review and approval
- One Application ID per platform environment — register separate Application IDs
  for dev, staging, and production; this prevents a misconfigured dev environment
  from accessing production credentials; PAM team tracks application access by
  Application ID in their audit reports
- Safe and Object naming convention — CyberArk organizes credentials into Safes
  (access-controlled vaults) and Objects (individual credentials); the platform
  adapter must know the Safe name and Object name for each credential it needs
  to check out; establish a naming convention with the PAM team: e.g.,
  `Safe=Platform-MCP-Tools`, `Object=github-enterprise-pat`

**What credential types does the adapter check out?**
- GitHub Enterprise PAT — stored in CyberArk as a password object; checked out
  at session init; injected into the GitHub MCP tool's authentication context;
  the same token is used for all GitHub tool calls within the session; checked
  in at session end
- Jira API token — same pattern as GitHub PAT; stored in CyberArk; checked out
  per session; injected into the Jira MCP tool context
- Database credentials (for internal tools) — CyberArk's automatic password
  rotation manages database accounts; the adapter checks out the current password
  at session init; the credential is valid for the session duration; CyberArk
  rotates the password on check-in if rotation policy requires it
- SSH private keys — for MCP tools that SSH into internal systems; CyberArk stores
  SSH private keys as file objects; the adapter checks out the key content, writes
  it to a tmpfs (in-memory filesystem) mount in the Lambda, and deletes it on
  session end; never written to disk or logged

**How are checked-out credentials returned at session end?**
- Explicit check-in via Lambda session end hook — the MCP gateway calls the
  credential-broker Lambda with a `session_end` event when a session terminates
  normally; the broker posts a reconcile request to CCP, signaling that the
  credential is no longer in use; CyberArk marks the credential as available for
  the next requestor
- TTL-based auto-expiry (backup) — CyberArk credentials checked out with a TTL
  expire automatically if not explicitly returned; set the checkout TTL to 110%
  of the platform's maximum session duration (e.g., if sessions cap at 4 hours,
  set TTL to 5 hours); if the Lambda dies without sending check-in, CyberArk
  reclaims the credential after TTL; prevents indefinite lockout
- Dead letter queue for failed check-ins — if the check-in Lambda invocation
  fails (CyberArk unreachable), send the check-in request to an SQS DLQ with
  a retry policy; the DLQ processor retries check-in with exponential backoff;
  ensures check-ins succeed eventually even if CyberArk is briefly unavailable

**How is the CyberArk integration audited?**
- CyberArk audit trail — every CCP credential checkout and check-in is logged
  in CyberArk's Vault audit log with: timestamp, Application ID, Safe, Object
  name, requester IP; this is CyberArk's native audit; the PAM team owns this log
- Platform session correlation — the credential-broker Lambda includes the
  platform `session_id` in the CCP request's `Reason` field (a free-text audit
  annotation accepted by CCP); this allows correlation between the CyberArk
  audit log entry and the platform session log; enables answering "which developer
  session used this credential and what tool calls were made"
- Platform audit event for each checkout — the credential-broker Lambda writes
  a structured audit event to the platform's CloudWatch log: `{ event: "credential_checkout", session_id: "...", safe: "...", object: "...", application_id: "...", timestamp: "..." }`; this is the platform's own record that a credential was checked out

**How does the adapter handle CyberArk unavailability?**
- Graceful degradation — same pattern as the Vault integration: if CCP is unreachable,
  the session starts but MCP tools requiring CyberArk credentials are removed from
  the tool allowlist; the agent operates with file system and local tools only;
  developer sees a clear message
- Hard fail for compliance-critical sessions — sessions on repos tagged `pci-scoped`,
  `sox-critical`, or `model-critical` must not start if CyberArk is unavailable;
  the credential requirement for these tools is a compliance control, not just
  a convenience; the adapter checks the repo's compliance tags and applies the
  appropriate failure mode

## Principles

- The PAM team is a dependency, not a blocker — CyberArk Application ID registration
  requires PAM team involvement; engage the PAM team in the platform design phase,
  not after the code is written; build the registration process into the platform
  deployment runbook; factor 1-2 weeks for each new environment registration
- Credentials never leave Lambda memory — credentials checked out from CyberArk
  are stored only in Lambda execution context variables; never written to logs,
  DynamoDB, S3, or environment variables; the Lambda execution role has no S3
  write permissions that could be used to persist a credential accidentally
- Check-in is as important as check-out — a credential left checked out in CyberArk
  is not just a security concern; it blocks other applications or rotation policies
  from using the credential; design the check-in path with the same care as the
  check-out path; test check-in under Lambda timeout, cold start, and network
  partition scenarios
- Correlate every checkout with a session ID — the `Reason` field in CCP requests
  is an audit mechanism; always populate it with the platform session ID; this is
  the only way to answer the security incident question "what did the user do with
  this credential"; without it, you have a CyberArk log entry with no platform context
- Application ID least privilege — the platform's Application ID should have access
  only to the Safes and Objects required by the MCP tools; it should not be granted
  access to the organization's broader CyberArk Safe hierarchy; work with the PAM
  team to define the minimum access set before registration

## Stack Options

**CyberArk CCP adapter runtime**
- AWS Lambda (recommended) — the `cyberark-credential-broker` Lambda is invoked
  at session init and on session end; VPC-deployed (CCP endpoint is typically
  on-premises or private network); Lambda security group allows outbound HTTPS
  to the CCP host only; Lambda execution role has no credential-related IAM
  permissions (all credential access is via CCP, not AWS services)
- ECS sidecar — for agent frameworks running on ECS; the credential-broker runs
  as a sidecar container; shares the task's network namespace with the agent
  container; communicates over localhost; better for long-running sessions where
  Lambda cold starts or container recycling could interrupt credential availability
- Direct SDK call from agent harness — simplest implementation: the agent harness
  calls CCP directly using the `cyberark-conjur` Python client or a plain HTTPS
  client; eliminates the separate Lambda; appropriate when the harness runs on
  ECS or GKE where the container can hold the client certificate and maintain
  the CCP connection

**CyberArk CCP client**
- Plain HTTPS client (recommended for simplicity) — CyberArk CCP exposes a
  simple REST endpoint: `GET /AIMWebService/api/Accounts?AppID=...&Safe=...&Object=...`;
  use Python `requests` with the client certificate: `requests.get(url, cert=(cert_path, key_path), verify=ca_bundle_path)`; no CyberArk SDK required; the response JSON contains the `Content` field (the credential value)
- `cyberark-conjur` Python SDK — for organizations using CyberArk Conjur (the
  cloud-native version of CyberArk); different API path than the legacy CCP;
  uses JWT-based authentication instead of certificates; appropriate when the
  organization has migrated to Conjur

**Client certificate management**
- ACM Private CA + Secrets Manager — the platform's Private CA issues the
  client certificate for the Application ID; certificate stored in Secrets Manager
  as a PKCS#12 bundle; Lambda fetches on cold start; ACM automation handles
  rotation 30 days before expiry; Lambda fetches the new certificate on the next
  cold start after rotation
- Certificate mounted via Lambda Powertools parameter store — for simpler setups;
  certificate stored as a SecureString in Parameter Store; fetched and cached
  for the Lambda container lifetime; rotation requires a Lambda redeploy or
  cache invalidation

**Session end hook**
- SQS session-end queue — the MCP gateway enqueues a `session_end` message to SQS
  when a session terminates; a Lambda polls the queue and invokes the CyberArk
  check-in call; decouples the session termination path from the check-in call;
  SQS DLQ with 5 retries handles transient CyberArk unavailability
- EventBridge session-end event — the gateway publishes a `session.ended` event
  to EventBridge; the credential-broker Lambda is subscribed; handles both normal
  and timeout terminations; EventBridge archives ensure no events are lost

**Conjur alternative**
- CyberArk Conjur OSS — for organizations using the modern CyberArk cloud-native
  platform; Conjur uses OIDC/JWT authentication instead of certificates;
  the Lambda authenticates with its IAM role's identity token; simpler certificate
  management; `conjur-api-python3` client library; `GET /secrets/{account}/variable/{path}`
  to retrieve a credential

## Connects to

- [MCP Gateway](mcpgw.md) — the CyberArk adapter plugs into the same credential
  injection point in the MCP gateway as the Vault adapter; the two adapters are
  alternatives (use one per environment); the gateway's tool routing and policy
  enforcement are unchanged regardless of which PAM system backs it
- [Vault Integration](vault-integration.md) — for enterprises considering both
  CyberArk and Vault: CyberArk is typically the PAM for privileged infrastructure
  credentials (database, SSH); Vault may be used for application secrets (API
  keys, service tokens); the platform may need both adapters simultaneously,
  routing credential requests to the appropriate system by credential type
- [Identity & Access](../access/identity.md) — the developer's IAM session
  context provides the `session_id` that flows into the CyberArk CCP `Reason`
  field; without a strong identity anchor, the CyberArk audit trail cannot be
  correlated with developer identity
- [Security Operations](../access/security-ops.md) — CyberArk credential checkout
  events are a key security signal; a developer session that checks out an unusual
  credential or makes an unusually high number of checkouts should trigger a
  SIEM alert; Security Operations owns the CyberArk-to-SIEM integration

## Sources

- [CyberArk Central Credential Provider REST API](https://docs.cyberark.com/credential-providers/latest/en/content/sdk/cyberark-application-identity-management-api.htm) — to verify on first use — AppID authentication; Safe/Object lookup; Reason field
- [CyberArk Application Identity Management](https://docs.cyberark.com/credential-providers/latest/en/content/cp-and-ascp/cyv-credentials-by-application-type.htm) — to verify on first use — application registration; allowed machines; certificate authentication
- [CyberArk Conjur documentation](https://docs.cyberark.com/conjur-enterprise/latest/en/content/home.htm) — to verify on first use — JWT authentication; secret retrieval API; OIDC integration
- [Python requests — client-side certificates](https://requests.readthedocs.io/en/latest/user/advanced/#client-side-certificates) — to verify on first use — cert tuple syntax; CA bundle verification
