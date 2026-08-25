---
type: platform-component
title: HashiCorp Vault Integration
description: integrating HashiCorp Vault as the credential source for MCP gateway tool call injection — replacing or complementing AWS Secrets Manager for enterprises where Vault is the standard PAM
group: gateway
tags: [gateway, vault, hashicorp, pam, secrets, credential-injection, aws-iam-auth, approle, dynamic-secrets]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [hashicorp-vault, vault, enterprise-secrets, no-secrets-manager, pam, vault-enterprise, privileged-access, secrets-management-standard]
decision-question: "Is HashiCorp Vault your enterprise secrets management standard — meaning the MCP gateway cannot inject credentials from AWS Secrets Manager alone, and must integrate with Vault's API to fetch tool credentials at session time?"
decision-domain: secrets_integration
priority: 7
requires: [gateway/mcpgw]
alternatives: [gateway/cyberark-integration]
---

HashiCorp Vault is the secrets management standard at many large enterprises
(financial services, technology, government contractors). The standard AgentCore
Gateway and most MCP gateway implementations inject credentials from AWS Secrets
Manager or IAM role assumption. When Vault is the enterprise standard, a custom
adapter is required: a component that authenticates to Vault, fetches the required
secret, and injects it into the MCP tool call context.

This is not a large build — it is a well-defined 1-2 sprint engineering task.
But it must be designed correctly from the start: poor Vault integration is a
common source of credential leaks (secrets logged in Lambda environment variables),
session reliability issues (token TTL mismatches), and audit gaps (Vault audit
log not correlated with platform session audit trail).

## How Vault Credential Injection Works

The credential injection flow replaces the Secrets Manager fetch with a Vault API
call at the same point in the session lifecycle:

```
Session init
  └── Lambda authorizer
        ├── Authenticate developer (Okta → IAM Identity Center)
        └── vault-credential-broker Lambda
              ├── Authenticate to Vault (AWS IAM auth method)
              ├── Fetch secret (KV v2, dynamic secret, or PKI cert)
              ├── Inject into MCP gateway tool context (in-memory only)
              └── Schedule refresh before Vault lease expiry

Session active
  └── MCP gateway tool call
        ├── Tool receives injected credential from session context
        └── On 401/403 response: trigger re-fetch (credential rotation detection)

Session end
  └── Vault lease revoke (optional but recommended for dynamic secrets)
```

## Decisions

**Which Vault auth method does the adapter use?**
- AWS IAM auth method — the Lambda function authenticates to Vault by signing
  an `sts:GetCallerIdentity` request with its IAM role credentials; Vault verifies
  the signature against AWS STS; the Lambda's IAM role is bound to a Vault policy;
  no static Vault token required anywhere; recommended for all Lambda-based adapters
  running on AWS; works across accounts with correct IAM role binding
- AppRole auth — Vault-native auth method; the adapter holds a Role ID (non-secret)
  and Secret ID (short-lived, pulled from Secrets Manager or injected at deploy time);
  more portable than AWS IAM auth but requires managing the Secret ID lifecycle;
  suitable for non-AWS execution environments (GCP, Azure, on-prem runners)
- Token auth (avoid in production) — static Vault token passed as an environment
  variable; simple for development; dangerous in production (token is a long-lived
  credential that can be logged or leaked); do not use for the platform adapter

**What type of secret does the adapter fetch?**
- KV v2 (static secrets with versioning) — for credentials that don't rotate
  automatically: GitHub PAT, Jira API token, internal API keys; Vault KV v2
  tracks version history; the adapter reads the current version at session init;
  if the secret is rotated in Vault, the next session gets the new value automatically
- Dynamic secrets (database, AWS, PKI) — Vault generates a short-lived credential
  on demand; the adapter requests a new credential at session start; Vault revokes
  it at session end; ideal for GitHub tokens (Vault GitHub secrets engine),
  database credentials, or AWS temporary credentials; eliminates standing credentials
  entirely; highest security posture
- PKI certificates — for MCP servers that authenticate via mTLS; Vault PKI engine
  issues short-lived client certificates; adapter fetches cert + key at session init;
  injects into the MCP tool's TLS configuration

**How is Vault token TTL managed relative to session duration?**
- Lease renewal before expiry — the adapter tracks the Vault token TTL and the
  secret lease TTL separately; a background goroutine or scheduled Lambda invocation
  renews the token before it expires; for dynamic secrets, request a new credential
  rather than renewing (renewal resets the lease, not the credential)
- TTL longer than maximum session duration — set the Vault token TTL to exceed
  the platform's maximum session duration (e.g., if sessions cap at 4 hours,
  set token TTL to 5 hours); simpler than renewal but means tokens are slightly
  over-issued; acceptable for KV v2 access where the token doesn't carry a
  database connection
- Re-authentication on expiry — if the token expires mid-session (e.g., developer
  left a session running overnight), the adapter re-authenticates using the AWS
  IAM auth method; requires the Lambda execution context to still be valid;
  re-authentication adds ~100ms latency on the re-fetch call

**How does the adapter handle Vault unavailability?**
- Graceful degradation — if Vault is unreachable at session init, the session
  starts but MCP tools requiring Vault-injected credentials are unavailable (removed
  from the tool allowlist for this session); the agent proceeds with file system
  tools and local capabilities only; the developer sees a clear message ("External
  tool credentials unavailable — Vault unreachable"); session is not failed entirely
- Hard fail — session cannot start if Vault is unreachable and credentials are
  required; suitable for regulated environments where the agent must not operate
  without full tool capability; simpler but creates a Vault availability dependency
  for all platform sessions
- Recommended: graceful degradation for developer productivity environments;
  hard fail for compliance-critical environments where operating without audit
  of all tool calls is unacceptable

**Where are Vault credentials stored during the session?**
- Lambda memory only — credentials fetched from Vault are stored as in-memory
  variables in the Lambda execution context; never written to disk, never logged,
  never stored in DynamoDB or S3; cleared when the Lambda container is recycled;
  this is the correct pattern
- Session context store with encryption — for longer sessions where the Lambda
  may be recycled between tool calls, store the credential in an encrypted
  DynamoDB item keyed by session ID; encrypt with a session-specific KMS data key;
  delete the item on session end; adds latency on cold paths but survives Lambda recycling

## Principles

- The Vault adapter is a credential broker, not a credential store — it fetches
  from Vault at session time and holds credentials in memory only; it does not
  cache credentials across sessions, does not write to Secrets Manager, and does
  not log credential values anywhere
- Vault audit log must be correlated with the platform session audit trail —
  every Vault secret access should include the platform session ID as metadata
  (passed as a Vault audit annotation or in the request path context); this enables
  correlation between "which developer used which credential" across both systems
- Dynamic secrets are the right long-term target — dynamic credentials (Vault
  generates, Vault revokes) eliminate standing credentials entirely; KV v2 is
  acceptable for credentials the platform doesn't control the lifecycle of (third-party
  SaaS API keys); use dynamic secrets wherever Vault has an engine for the target system
- The adapter's IAM role must be least-privilege — the Lambda's IAM role should
  be bound to a Vault policy that reads only the paths required by platform MCP tools;
  not a broad Vault admin role; test by listing the policies and verifying each path
- Vault availability is a platform dependency — design for it; Vault Enterprise
  has DR replication; Vault OSS can run with Raft HA; the graceful degradation
  pattern reduces the blast radius of a Vault outage but does not eliminate it

## Stack Options

**Vault adapter runtime**
- AWS Lambda (recommended) — the `vault-credential-broker` Lambda is invoked at
  session init and on credential refresh; uses AWS IAM auth method (no static
  credentials needed); execution role is bound to the Vault policy; function
  timeout set to 10 seconds (Vault API call is fast; timeout is a safety net);
  Lambda concurrency matches platform session concurrency; reserve concurrency
  to prevent Vault flooding
- ECS sidecar — for agent frameworks running on ECS (Strands, LangChain on ECS);
  a Vault agent sidecar container runs alongside the agent; Vault agent handles
  auth and lease renewal natively; writes secrets to a shared in-memory tmpfs
  volume; the agent reads from the tmpfs path; Vault agent's built-in renewal
  logic handles TTL management; the most robust pattern for long-running sessions

**Vault auth methods**
- AWS IAM auth method — `vault auth enable aws`; bind the Lambda role ARN to a
  Vault role with the required policy; no credentials needed in Lambda; automatic
  rotation via STS; works cross-account (Lambda in account A, Vault in account B
  or on-premises) with correct IAM role trust
- AppRole — `vault auth enable approle`; generate Role ID at deploy time; Secret ID
  generated dynamically (response-wrapping recommended); inject Secret ID via
  Secrets Manager (one secret to bootstrap the rest); suitable for GCP Cloud Run,
  Azure Container Apps, or on-premises runners where AWS IAM auth is not available

**Vault secrets engines**
- KV v2 — `vault secrets enable -path=platform kv-v2`; store GitHub PATs, Jira
  tokens, API keys; metadata versioning; adapter reads `platform/data/github-token`
  at session init
- AWS secrets engine — `vault secrets enable aws`; Vault generates temporary AWS
  credentials (STS AssumeRole); adapter requests IAM credentials scoped to the
  tool's required permissions; Vault automatically revokes when lease expires;
  useful for MCP tools that need AWS API access
- Database secrets engine — for MCP tools that query internal databases; Vault
  generates a short-lived database username/password; tool uses it; Vault revokes
  on lease expiry; no standing database credentials

**Session context encryption (if needed across Lambda recycling)**
- DynamoDB + KMS — session item in DynamoDB; credential value encrypted with
  `aws:datakey` using the session KMS CMK; item TTL set to session max duration;
  CMK key policy restricts decryption to the adapter Lambda role only

**Vault HA for production**
- Vault Enterprise with Performance Replication — recommended for enterprise
  deployments where Vault is a platform dependency; replication ensures Vault
  availability in the same region as the platform
- Vault OSS with Raft integrated storage — for organizations not on Vault Enterprise;
  3-node Raft cluster; automatic leader election; no external storage dependency;
  sufficient for platform-scale credential volumes

## Connects to

- [MCP Gateway](mcpgw.md) — the Vault adapter plugs into the MCP gateway's
  credential injection point; it replaces or supplements the Secrets Manager fetch;
  the gateway's tool call routing and allowlist enforcement are unchanged
- [Identity & Access](../access/identity.md) — the developer's IAM session token
  (from IAM Identity Center) is the anchor identity for Vault auth; the adapter
  uses the session context to construct the Vault auth request
- [Security Operations](../access/security-ops.md) — Vault audit log is a key
  security signal; compromise of a Vault credential used in a platform session
  requires correlating the Vault audit log with the platform session audit trail
- [On-Premises Runner](../exec/on-prem-runner.md) — air-gapped and on-premises
  runners use Vault OSS as the secrets backend when AWS Secrets Manager is not
  reachable; AppRole auth is the on-prem auth method

## Sources

- [HashiCorp Vault AWS IAM auth method](https://developer.hashicorp.com/vault/docs/auth/aws) — to verify on first use — IAM auth configuration; binding Lambda roles to Vault policies
- [HashiCorp Vault agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent) — to verify on first use — sidecar pattern; auto-auth; template rendering; lease renewal
- [HashiCorp Vault KV v2 secrets engine](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2) — to verify on first use — versioned KV; metadata; read/write API
- [HashiCorp Vault AWS secrets engine](https://developer.hashicorp.com/vault/docs/secrets/aws) — to verify on first use — dynamic AWS credentials; STS AssumeRole; lease TTL
