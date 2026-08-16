---
type: platform-component
title: IdP Federation at Scale
description: broker-pattern identity federation for enterprises with multiple identity providers, acquisitions, or legacy directory systems
group: access
tags: [access, identity, idp, federation, okta, entra, saml, oidc, acquisition, enterprise]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [multiple-idps, idp-federation, acquisition-identity, legacy-directory, 11-idps, active-directory-forest, saml-federation, oidc-federation, enterprise-sso]
decision-question: "Do you have more than one identity provider — through acquisitions, BU autonomy, or legacy AD forests — that must all grant access to the coding agent platform without requiring a monolithic IdP consolidation first?"
---

Enterprise identity sprawl is the norm at scale: a 20,000-developer organization
may have 5–15 active identity providers — an Okta corporate tenant, an Azure Entra
tenant from an acquisition, several legacy Active Directory forests, a Ping Federate
instance in a regulated BU, and remnants of a prior LDAP consolidation that never
finished. Forcing IdP unification before platform deployment is a multi-year bloat
dependency that blocks value delivery.

The broker pattern resolves this: a **central identity broker** (AWS IAM Identity
Center, or a dedicated federation hub like Okta as orchestrator) accepts inbound
tokens from all upstream IdPs and issues a single normalized claim set to the
platform. The platform trusts one issuer. Each BU authenticates through their
existing IdP without migration.

## The Federation Topology

```
BU-A Okta tenant ──────────────┐
BU-B Azure Entra ──────────────┤
Legacy AD Forest 1 ────────────┤──► Central Broker ──► Platform IAM ──► Agent session
Legacy AD Forest 2 ────────────┤    (IAM Identity      (single trust
Acquired-Co Ping Federate ─────┤     Center or          boundary)
GCP Workspace (acquired) ──────┘     Okta tenant)
```

The broker issues a normalized JWT with a consistent claim schema regardless of
which upstream IdP authenticated the developer. Platform IAM policies reference
claims from the broker — never from individual upstream IdPs directly.

## Decisions

**What serves as the central broker?**
- AWS IAM Identity Center as broker — configure each upstream IdP as an external
  identity source (SAML 2.0 or OIDC) in IAM Identity Center; IAM Identity Center
  issues session credentials for AWS resources; best choice when the platform runs
  entirely on AWS; each BU connects their IdP without any platform migration
- Okta as orchestrator with IAM Identity Center downstream — Okta's Workforce
  Identity Cloud accepts inbound federation from many upstream IdPs via Okta
  Identity Engine (OIE) policies; Okta then federates to IAM Identity Center as a
  single SAML/OIDC source; adds vendor cost but provides richer policy engine for
  claim transformation and conditional access
- Azure Entra External Identities as broker — if the enterprise's dominant IdP is
  Azure Entra, configure it as the broker; other IdPs federate into Entra; IAM
  Identity Center trusts Entra as external IdP; natural choice post-acquisition
  when the acquired entity's Entra is larger than the parent's

**How are claims normalized across IdPs?**

Each upstream IdP uses different attribute names for the same concepts
(e.g., `employeeType` vs `userType` vs `jobCode`). The broker must normalize:

| Raw upstream claim | Normalized broker claim | Platform uses |
|---|---|---|
| `employeeType=FTE` / `userType=employee` | `employment_type=fte` | Policy scoping |
| `department` / `dept` / `ou` | `business_unit` | Cost attribution |
| `countryCode` / `country` / `co` | `country_iso` | Jurisdiction routing |
| `usPersonFlag` / `usNational` | `us_person=true` | ITAR gate |
| `clearanceLevel` / `securityClearance` | `clearance_tier` | Restricted repo access |

Claim transformation rules live in the broker as code (Okta Expression Language,
IAM Identity Center attribute mappings, or a Lambda claim transformer). Keep them
in source control alongside the platform.

**How are claim transformations governed?**
- Broker-native attribute mapping UI — fast to configure; hard to audit; changes
  are not version-controlled; acceptable for small federation topologies
- IaC-managed attribute mappings (Terraform or CloudFormation) — all claim
  transformation rules declared as code; changes go through PR review; recommended
  for any federation topology with 3+ upstream IdPs or compliance requirements
- Lambda claim transformer (custom) — for complex transformation logic that
  broker-native mapping cannot express; a Lambda runs as a pre-token-issuance hook;
  testable, version-controlled, auditable; adds latency (~50ms)

**How are group memberships harmonized?**
- Group-per-BU prefix convention — each upstream IdP prefixes group names with BU
  identifier (e.g., `BU-A::platform-users`); broker passes prefixed groups; platform
  policies match on prefix pattern; avoids group name collisions across IdPs
- Centralized group registry — a single authoritative group definition in the broker;
  upstream IdP group membership maps to broker groups via transformation rules;
  stronger consistency, more maintenance overhead

**What is the onboarding path for a new acquisition?**
- Standard acquisition runbook — documented sequence: (1) create SAML/OIDC app
  registration in acquired IdP, (2) configure as new upstream in broker, (3) define
  claim mapping for that IdP, (4) assign acquired-company developers to broker groups,
  (5) validate with a canary developer before bulk enrollment; target: 2-week
  onboarding to platform access without IdP migration

**How is session token lifetime managed across IdPs?**
- Platform enforces maximum session duration independent of upstream IdP token TTL —
  even if an upstream IdP issues 8-hour tokens, platform sessions are capped at the
  policy maximum (e.g., 4 hours for standard, 1 hour for restricted repos); enforced
  at the broker or Lambda authorizer layer

## Principles

- The platform trusts one issuer (the broker), never individual upstream IdPs directly —
  this keeps platform IAM policies simple and consistent; adding a new upstream IdP
  means updating the broker, not the platform
- Claim normalization is the foundational dependency for every downstream access control —
  ITAR US-person checks, jurisdiction routing, policy tier assignment, and cost attribution
  all depend on normalized claims; get the claim schema right before building downstream
  policies
- Federation topology is not a migration plan — the broker pattern is a durable
  architecture, not a temporary bridge; plan for the acquired company's IdP to be a
  permanent upstream source for 3–5 years; design accordingly
- Every upstream IdP connection is a trust relationship — document each one, review it
  annually, and have an offboarding procedure; unused upstream connections are an
  attack surface
- Acquisition identity onboarding must not block platform access — the standard
  runbook should enable a new company's developers to access the platform within
  2 weeks of acquisition close, without waiting for directory consolidation

## Stack Options

**Central broker**
- AWS IAM Identity Center — native AWS broker; supports multiple external IdPs via
  SAML 2.0 and OIDC; attribute sync for user metadata; free within AWS; permission
  sets map to IAM roles; best fit for AWS-native platform deployments
- Okta Workforce Identity Cloud (OIE) + IAM Identity Center downstream — Okta as
  orchestrator accepting inbound federation from legacy AD, Ping, other Okta tenants;
  rich conditional access policy engine; Okta → IAM Identity Center via SAML; adds
  licensing cost but handles complex claim transformation requirements
- Azure Entra External Identities — if Entra is the enterprise anchor IdP; configure
  other IdPs as B2B or external identity sources; Entra → IAM Identity Center via
  OIDC/SAML; natural for post-acquisition scenarios where the acquired entity has
  the larger Entra footprint

**Claim transformation**
- IAM Identity Center attribute mappings — map upstream SAML attributes to IAM
  session tags natively; no Lambda required; limited transformation logic; covers
  most standard attribute rename scenarios
- Okta Expression Language (OEL) — scripted attribute transformation in Okta; runs
  before token issuance; supports conditional logic (e.g., map `countryCode` from
  3 different upstream attribute names to one normalized claim)
- AWS Lambda pre-token hook — custom Lambda invoked by Cognito or a custom OIDC
  proxy before token issuance; full programmatic control; handles complex scenarios
  (e.g., HR system enrichment, multi-source claim merging); adds ~50ms latency

**Group management**
- IAM Identity Center permission sets — map broker groups to permission sets; each
  permission set defines the IAM role the developer assumes in each AWS account;
  supports multi-account org topologies
- AWS Organizations SCPs + IAM Identity Center — layer SCPs at the OU level for
  coarse-grained policy, permission sets for fine-grained; prevents IAM Identity
  Center permission escalation even if claim transformation has a bug

**Acquisition onboarding automation**
- Terraform module: `platform-idp-onboarding` — parameterized module that provisions
  SAML/OIDC app registration in IAM Identity Center, defines attribute mapping rules,
  and assigns default permission set for new acquisition; onboarding a new IdP
  becomes a PR with new variable values; reviewed, applied, done
- AWS Service Catalog product — package the onboarding Terraform as a Service Catalog
  product; acquisition IT teams self-serve the onboarding with guardrails; reduces
  platform team toil

**Session audit**
- AWS CloudTrail — logs every IAM Identity Center authentication event with source
  IdP identifier, user identity, and session token issuance; cross-reference with
  platform session logs to build full identity chain per session
- Amazon EventBridge rule on IAM Identity Center sign-in events — trigger alerts
  on authentication from unusual upstream IdPs or unexpected geographic locations

## Connects to

- [Identity & Access](identity.md) — this node extends the base identity model to
  multi-IdP topologies; identity.md defines the workload identity model, this node
  defines how developer identities from multiple sources are normalized before
  reaching the platform
- [Export Control (ITAR/EAR)](export-control.md) — US-person status verification
  at session time depends on a normalized `us_person` claim propagated correctly
  through the federation chain; broken claim mapping = ITAR enforcement gap
- [Policy Tiers](policy-tiers.md) — tier assignment logic reads normalized claims
  (BU, employment type, clearance); requires consistent claim schema across all
  upstream IdPs
- [Multi-Cloud Governance](../ops/multi-cloud-governance.md) — cross-cloud identity
  federation is an extension of this broker pattern; the same broker that unifies
  multiple enterprise IdPs also federates to Azure Entra for the multi-cloud case

## Sources

- [AWS IAM Identity Center — manage external identity provider](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-idp.html) — to verify on first use — configuring multiple upstream IdPs
- [IAM Identity Center attribute mappings](https://docs.aws.amazon.com/singlesignon/latest/userguide/attributemappingsconcept.html) — to verify on first use — claim transformation from upstream SAML attributes to IAM session tags
- [Okta Identity Engine (OIE) — inbound federation](https://developer.okta.com/docs/concepts/identity-providers/) — to verify on first use — Okta as orchestrator for multiple upstream IdPs
- [AWS Organizations + IAM Identity Center multi-account architecture](https://docs.aws.amazon.com/singlesignon/latest/userguide/multi-account-permissions.html) — to verify on first use
