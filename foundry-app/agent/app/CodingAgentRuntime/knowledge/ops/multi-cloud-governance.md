---
type: platform-component
title: Multi-Cloud Governance
description: consistent policy, identity, observability, and cost attribution across AWS, Azure, and GCP platform instances
group: ops
tags: [ops, multi-cloud, azure, gcp, governance, acquisition, policy-as-code]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [multi-cloud, azure-acquisition, gcp-workloads, cloud-agnostic, acquisition-integration, existing-azure, existing-gcp]
decision-question: "Do you have engineering teams on Azure or GCP — through acquisitions or existing investments — that need to be governed under the same platform policy without requiring an AWS migration?"
---

Multi-cloud governance applies when a coding agent platform must extend to
engineering workloads running on non-AWS cloud infrastructure — most commonly
acquired companies on Azure, existing GCP deployments, or regulatory requirements
that mandate specific cloud providers in specific regions.

The goal is **governance parity without infrastructure migration**: the same
security policies, identity model, cost attribution, and audit trail — regardless
of which cloud the agent runs on. The platform team enforces the governance layer;
the underlying infrastructure can differ by cloud.

## The Acquisition Scenario

The most common trigger: an acquired company runs on Azure (GitHub Enterprise
on Azure, Azure DevOps, Azure Container Apps). Forcing an immediate AWS migration
disrupts an already-stressed integration. The platform extends governance to their
Azure footprint while migration is planned or deferred indefinitely.

The two-option framework:

| Option | What it means | When to choose |
|---|---|---|
| **OSS framework on Azure** | Deploy Strands or LangChain on Azure Container Apps; federate identity to central IdP broker; route inference through Azure OpenAI or Bedrock cross-cloud (via public endpoint); apply OPA policy at the Azure deployment | Acquired team will stay on Azure 12+ months; governance parity matters more than infrastructure uniformity |
| **Governance overlay only** | Accept the existing Azure deployment as-is for now; apply OPA policy-as-code externally; aggregate logs to central SIEM; plan migration | Acquisition integration period is short; migration is realistic within 6 months; minimise new build |

## Decisions

**Governance approach?**
- Policy-as-code overlay (OPA/Rego) — write Rego policies that express the
  platform's security rules in a cloud-agnostic way; enforce them as admission
  controllers or sidecar validators on each cloud; the same policy file governs
  AWS and Azure; policies live in a central git repo versioned alongside the
  platform
- Native cloud controls per instance — configure each cloud's native IAM,
  security groups, and logging independently; harder to keep consistent;
  acceptable only if the non-AWS deployment is genuinely temporary and small

**Identity federation across clouds?**
- Central IdP → each cloud's IAM — Okta (or Entra as central IdP) federates
  outbound to both AWS IAM Identity Center and Azure Entra (for the Azure
  instance); developers have one login; each cloud trusts the same SAML/OIDC
  tokens; agent identity on each cloud is derived from the same workload
  identity model
- Separate IdP per cloud — simplest per-cloud setup; hard to maintain consistent
  access policy; developers manage multiple credentials; not recommended for any
  deployment expected to last more than a few months

**Observability unification?**
- Central SIEM aggregation — each cloud instance exports logs to a central SIEM
  (Splunk, Datadog, Elastic); CloudTrail from AWS, Azure Monitor from Azure, GCP
  Cloud Logging from GCP; all normalized to a common schema; one query surface
  for the security team
- Per-cloud dashboards — simpler to set up, acceptable for a temporary non-AWS
  deployment; creates a blind spot if an incident spans clouds

**Cost attribution across clouds?**
- Common tagging taxonomy — enforce the same cost tags (`team`, `bu`, `service`)
  on all cloud resources regardless of provider; each cloud's billing exports
  land in a central data warehouse (e.g., AWS Cost and Usage Report + Azure Cost
  Management export → S3 → Athena); one cost view across clouds
- Separate billing per cloud — simpler; harder to do cross-cloud chargeback;
  finance team must reconcile manually

**Inference routing for the non-AWS instance?**
- Azure OpenAI Service — if the acquired team is on Azure, use Azure OpenAI for
  inference; keeps inference traffic within the Azure boundary; governance
  applied at the LiteLLM layer running on Azure
- Amazon Bedrock via public endpoint — route inference from the Azure instance
  through the public Bedrock endpoint; data leaves Azure; adds latency; check
  data residency implications before enabling
- Self-hosted model on Azure (Strands + open-weight model) — for air-gapped or
  strict data residency requirements on Azure; highest ops burden; use only when
  inference cannot leave the Azure boundary

## Principles

- "One platform" at the governance layer, not the infrastructure layer — the
  mandate is consistent policy enforcement and a unified audit trail, not
  identical compute topology; satisfy the mandate without forcing migrations
  that disrupt acquisitions
- Policy-as-code is the governance mechanism that makes multi-cloud feasible —
  OPA/Rego policies version-controlled in git and deployed as containers run
  on any cloud; the alternative (native controls per cloud) creates N separate
  governance surfaces that inevitably drift
- Migration debt is a real cost — a "temporary" Azure deployment that becomes
  permanent is a governance liability; set a migration date at decision time,
  review it quarterly, and build the migration path into the roadmap even if
  execution is deferred
- Cost attribution must span clouds from day one — retrofitting a unified tagging
  taxonomy after two years of multi-cloud spend is painful; enforce tags as
  a policy-as-code rule that blocks resource creation without required tags

## Stack Options

**Policy-as-code (AWS and Azure)**
- Open Policy Agent (OPA) + Rego — CNCF project; cloud-agnostic; deploys as
  a sidecar container alongside the agent runtime on any cloud; Rego policies
  express guardrail rules, access control decisions, and resource constraints
  in a declarative language; the same policy bundle governs AWS ECS tasks and
  Azure Container Apps
- AWS Config + Azure Policy — native cloud compliance tools; write rules in
  each cloud's native language; harder to keep consistent; better for
  infrastructure compliance than for runtime agent policy enforcement

**Identity federation**
- Okta as central IdP → AWS IAM Identity Center + Azure Entra B2B federation —
  single Okta tenant; SAML federation to both clouds; developers authenticate
  once; both clouds trust the same Okta tokens; agent workload identities derived
  from IAM roles (AWS) and Managed Identities (Azure) both mapped to the same
  developer identity
- AWS IAM Identity Center with Azure as external IdP — if Azure Entra is the
  enterprise IdP (common post-acquisition), configure it as an external IdP in
  IAM Identity Center; AWS trusts Azure-issued tokens; simpler than dual-IdP
  federation

**OSS agent framework on Azure**
- Strands Agents on Azure Container Apps — deploy the same Strands agent code
  to Azure Container Apps (serverless containers); configure to use Azure OpenAI
  for inference; MCP servers deployed as Azure Container Apps sidecars; managed
  identity for credential injection (no static API keys)
- LangChain on Azure Functions — event-triggered agent tasks; 10-minute timeout
  limit on Consumption plan; use Premium plan for longer sessions; integrates
  natively with Azure DevOps and GitHub Enterprise on Azure

**Observability unification**
- Splunk with CloudWatch + Azure Monitor inputs — Splunk HEC accepts events from
  both sources; CloudTrail → Firehose → Splunk; Azure Monitor → Event Hub →
  Splunk Add-on; single Splunk dashboard for cross-cloud audit queries
- Datadog multi-cloud agent — deploy the Datadog agent on both AWS and Azure
  compute; single Datadog tenant aggregates APM, logs, and metrics from both
  clouds; lower configuration overhead than Splunk for greenfield multi-cloud
- OpenTelemetry collector per cloud → central backend — deploy an OTel collector
  on each cloud; export to a single observability backend (Grafana, Datadog,
  or Honeycomb); OTel is cloud-agnostic by design; normalizes log and trace
  schemas across providers automatically

**Cost unification**
- AWS Cost and Usage Report + Azure Cost Management export → S3 → Amazon Athena
  — both billing exports land in S3; Athena queries across both; build a
  QuickSight dashboard for cross-cloud cost attribution; requires consistent
  tagging taxonomy enforced by OPA
- CloudHealth / Apptio Cloudability — third-party FinOps platforms that natively
  aggregate AWS + Azure + GCP billing; easier to set up than a custom pipeline;
  adds a vendor dependency

**Migration planning**
- AWS Application Migration Service (MGN) — for migrating workloads from Azure
  to AWS when the transition window opens; agent framework code is already
  cloud-agnostic (Strands/LangChain), so migration is primarily infra + data,
  not code rewrite
- Terraform (cloud-agnostic IaC) — declare infrastructure in Terraform from day
  one, even for the Azure deployment; when migration happens, the Terraform
  module is ported, not rebuilt

## Connects to

- [Identity & Access](../access/identity.md) — cross-cloud identity federation
  is an extension of the identity model; the IdP federation broker is the key
  dependency
- [Observability & Audit](observability.md) — cross-cloud log aggregation is
  the mechanism that gives the central SIEM visibility into non-AWS instances;
  without it, multi-cloud governance is invisible governance
- [Cost Management](cost.md) — cross-cloud cost attribution requires a unified
  tagging taxonomy enforced from day one; cost.md defines the attribution model,
  this node defines how to extend it across clouds
- [Security Operations](../access/security-ops.md) — incidents that span clouds
  (e.g., a compromised MCP server on Azure affecting an AWS-hosted codebase)
  require a cross-cloud incident response capability; the unified SIEM is the
  prerequisite

## Sources

- [Open Policy Agent](https://www.openpolicyagent.org/docs/latest/) — to verify on first use — cloud-agnostic policy-as-code; Rego language; sidecar and admission controller deployment patterns
- [AWS IAM Identity Center external IdP configuration](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-idp.html) — to verify on first use — Azure Entra as external IdP trusted by IAM Identity Center
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview) — to verify on first use — serverless containers on Azure; suitable for Strands/LangChain deployment in acquired-company footprints
- [Strands Agents documentation](https://strandsagents.com/latest/) — to verify on first use — cloud-agnostic deployment; runs on Azure Container Apps as well as AWS
