---
type: platform-component
title: Platform Instance Federation
description: governing multiple platform instances as one federated platform — consistent policy, shared identity, unified observability, and instance lifecycle management across BU or regional deployments
group: ops
tags: [ops, federation, multi-instance, platform-governance, bу-autonomy, instance-management, policy-synchronization]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [multi-instance, platform-federation, multiple-bus, regional-instances, instance-governance, one-platform-mandate, federated-platform, bу-instances, instance-drift]
decision-question: "Are you operating — or planning to operate — more than one platform instance across BUs, regions, or jurisdictions, and do you need to govern them as a single federated platform rather than independent deployments?"
---

When a coding agent platform scales beyond a single BU or region, it inevitably
fragments into multiple instances: one per major BU, one per regulated jurisdiction,
one for a post-acquisition footprint. Without a federation governance model, these
instances drift: different guardrail versions, different tool allowlists, different
quota policies, different identity trust configurations. The "one platform" mandate
becomes aspirational rather than operational.

Platform instance federation is the answer to: **how do you maintain governance
parity across N instances without requiring them to be identical or centrally
managed?**

The answer is a **hub-and-spoke governance model**: a central platform team
(the hub) owns the policy canon — the baseline guardrails, the identity trust
configuration, the security posture requirements, the audit schema. Each instance
(a spoke) inherits the canon but may have instance-local overrides within defined
bounds. The override space is explicit, bounded, and auditable.

## Federation Topology Reference

```
Central Platform Team (Hub)
├── Policy Canon Repository (OPA/Rego bundles, guardrail configs)
├── Identity Broker (IAM Identity Center + IdP federation)
├── Central SIEM (aggregated audit trail)
└── Instance Registry (which instances exist, their tier, their overrides)

Spoke Instances:
├── Global Commercial (us-east-1, standard developer population)
├── EU Regional (eu-central-1, GDPR-compliant, works council agreement)
├── GovCloud/ITAR (us-gov-east-1, US-person only, ITAR repos)
├── China (AWS China / Alibaba Cloud, PIPL-compliant, separate IdP)
└── Acquired-Company (Azure Container Apps, governance overlay)
```

## Decisions

**What is the canonical policy distribution mechanism?**
- OPA bundle server — the central platform team maintains a git repository of
  OPA/Rego policy bundles; a bundle server (AWS S3 + CloudFront, or a dedicated
  OPA bundle server) serves signed policy bundles to each instance's OPA sidecar;
  instances poll for updates; policy changes deploy to all instances simultaneously
  via a single push to the bundle repo; the gold standard for multi-instance policy
  governance
- AWS AppConfig — store guardrail configurations as AppConfig profiles; each
  instance polls AppConfig for its configuration profile; AppConfig supports
  gradual deployments (deploy to one instance, validate, then roll out to others);
  suitable for JSON/YAML config that doesn't require Rego logic
- GitOps with per-instance Terraform modules — a root module defines the canonical
  platform; per-instance modules inherit from the root with override variables;
  Terraform plan shows exactly what each instance's configuration is; applied via
  CI/CD pipeline

**What overrides are instances permitted to make?**

The canon defines the floor; instances can raise it, not lower it:

| Setting | Canon defines | Instance override permitted? |
|---|---|---|
| Guardrail baseline (blocked topics, DLP tiers) | Minimum guardrail set | Can add stricter rules; cannot remove canon rules |
| Tool allowlist | Approved tools (core set) | Can restrict to subset; cannot add tools not in canon |
| Quota ceilings | Maximum allowed spend | Can lower; cannot raise above canon ceiling |
| Identity trust (IdP broker) | Trusted issuer | Cannot change; all instances trust the same broker |
| Audit schema | Required log fields | Cannot remove fields; can add instance-specific fields |
| Session isolation model | Minimum isolation tier | Can raise; cannot lower |

Codify these constraints as OPA policies in the canon itself: a policy that
validates other policies. Any instance attempting to deploy a guardrail config
that is weaker than the canon baseline fails the validation gate.

**How are new instances provisioned and registered?**
- Instance registry — a central registry (DynamoDB table or SSM Parameter Store)
  records every live instance: instance ID, region/cloud, BU owner, compliance
  tier, allowed override set, canonical policy version, last-sync timestamp; the
  registry is the authoritative list of what exists
- Instance provisioning via IaC template — new instances are provisioned from a
  Terraform or CDK template that enforces the canon configuration; the template
  is the only approved provisioning path; instances created outside the template
  are not registered and cannot connect to the identity broker
- Instance health check — a scheduled Lambda queries each instance's OPA bundle
  version and configuration hash; alerts when an instance is running a stale
  policy version or has drifted from its registered configuration

**How is instance drift detected and remediated?**
- Policy version check — each instance OPA sidecar reports the policy bundle
  version it is running; the central registry alerts when any instance is more
  than N versions behind the canon; automated remediation: force-pull the latest
  bundle; manual remediation: investigate why the instance stopped polling
- Configuration drift detection — EventBridge + Config rules on the spoke accounts
  detect configuration changes (security group modifications, IAM policy changes,
  guardrail config mutations); changes outside the IaC pipeline trigger an alert
  to the central platform team
- Quarterly instance audit — platform team reviews all registered instances against
  the canon; documents approved deviations; decommissions instances that are
  no longer needed

**How is the audit trail unified across instances?**
- Log aggregation to central SIEM — each instance exports its audit logs (session
  events, tool calls, access events) to the central SIEM; common log schema
  ensures queries work across instances; instance identifier is a mandatory field
  on every log record (see observability.md for the pipeline)
- Cross-instance incident correlation — when a security incident occurs on one
  instance, the central SIEM can query whether the same actor, tool, or prompt
  pattern appeared on other instances; this is the key operational benefit of
  unified logging

**How are instance decommissions handled?**
- Decommission checklist — instance decommission requires: (1) drain active sessions,
  (2) export all audit logs to long-term retention before instance termination,
  (3) remove instance from identity broker trust (revoke permission set assignments),
  (4) update instance registry, (5) notify central SIEM that instance is gone;
  each step is a signed-off action in the ops runbook

## Principles

- The canon is the minimum, not the average — the central policy is the security
  floor; instances that need stricter controls (ITAR, China, regulated BU) add
  to it; instances that want looser controls accept the canon or escalate to the
  platform governance board for a formal exception
- Instances are cattle, not pets — every instance is provisioned from the same
  IaC template; no snowflake configurations; if an instance needs a special
  configuration, that configuration is added to the template with a feature flag,
  not applied manually; manual configuration = drift
- The instance registry is the authoritative inventory — if it's not in the registry,
  it doesn't exist from a governance perspective; shadow instances (provisioned
  outside the template) are a governance liability and a security risk; enforce
  registration as a prerequisite for identity broker access
- Policy updates must be testable before deployment — a canon policy change that
  breaks an instance is worse than the original gap; maintain a policy test suite
  (OPA unit tests + integration tests); run tests in CI before promoting a bundle
  version to production instances
- Multi-cloud instances follow the same canon — the OPA/Rego policy bundle that
  governs the AWS instance is the same bundle deployed to the Azure Container Apps
  instance; cloud-agnostic policy-as-code is the prerequisite for multi-cloud
  governance parity

## Stack Options

**Policy canon distribution**
- OPA bundle server on S3 + CloudFront — store signed Rego bundles in S3; serve
  via CloudFront with signed URLs; OPA sidecar on each instance configured with
  bundle URL and signing key; instances poll every 60 seconds; bundle signature
  prevents tampering; zero additional infrastructure required beyond S3 and CloudFront
- AWS AppConfig — managed configuration distribution with deployment strategies
  (linear, canary, all-at-once); built-in rollback; instances use the AppConfig
  SDK to receive configuration; suitable for JSON/YAML guardrail configs; combine
  with OPA for policy logic
- HashiCorp Vault — if the enterprise already runs Vault; store policy bundles as
  Vault secrets; instance auth via AWS IAM auth method; Vault provides access audit
  trail for every bundle fetch

**Instance registry**
- DynamoDB global table — instance registry stored in a multi-region DynamoDB table;
  accessible from any spoke account via cross-account IAM role; supports instance
  health check queries (scan by `last_sync_timestamp` attribute); PITR enabled for
  audit trail
- AWS Systems Manager Parameter Store — simpler alternative; store instance metadata
  as versioned parameters; version history is automatic audit trail; sufficient for
  fewer than 20 instances; DynamoDB preferred for larger fleets

**Configuration drift detection**
- AWS Config conformance packs — deploy conformance packs to each spoke account from
  the management account using AWS Organizations; conformance pack defines the
  required configuration rules; non-compliant resources reported to AWS Security Hub
  in the central account; cross-account Security Hub aggregation gives one view
- AWS Config aggregator — aggregates Config compliance results from all spoke accounts
  into the central account; Security Hub aggregation on top provides cross-instance
  compliance dashboard

**Cross-instance audit trail**
- Amazon Security Lake — collect logs from all instances (CloudTrail, VPC Flow Logs,
  Bedrock invocation logs) in OCSF format in a central Security Lake in the management
  account; instances contribute via cross-account Log Archive; Security Lake
  normalizes log schema across instances automatically
- OpenSearch cross-cluster search — if instances run their own OpenSearch for local
  querying, configure cross-cluster search to allow the central SIEM to query all
  instances from a single query surface; useful for incident investigation

**Instance provisioning**
- AWS CDK pipelines with instance parameter sets — define the platform stack in CDK;
  parameterize instance-specific settings (region, compliance tier, IdP config);
  a CDK pipeline per instance applies from the same codebase; instance parameters
  are the only diff between instances; reviewed in PR before application
- AWS Service Catalog + Terraform — package the instance Terraform as a Service
  Catalog product; BU platform owners self-serve instance provisioning from the
  approved product; guardrails enforced by the product template; instance
  registration triggered by a CloudFormation custom resource on provisioning completion

## Connects to

- [Multi-Cloud Governance](multi-cloud-governance.md) — instances on Azure or GCP
  are a special case of the federation model; OPA/Rego policy-as-code makes
  cross-cloud instances first-class citizens of the federation
- [Observability & Audit](observability.md) — cross-instance log aggregation is
  the operational mechanism that makes the federation visible; without it,
  the central platform team is governing blind
- [Identity & Access](../access/identity.md) — the identity broker is a shared
  federated component; all instances trust the same issuer; IdP federation is
  the identity layer of the federation model
- [Data Jurisdiction](../access/data-jurisdiction.md) — data jurisdiction requirements
  drive instance topology; China and ITAR instances exist because of jurisdiction
  constraints; federation governance must respect instance isolation requirements

## Sources

- [Open Policy Agent — bundle distribution](https://www.openpolicyagent.org/docs/latest/management-bundles/) — to verify on first use — OPA bundle server pattern; signed bundles; polling configuration
- [AWS Config aggregator](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html) — to verify on first use — cross-account compliance aggregation
- [AWS Organizations — delegated administrator for Config](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services_list.html) — to verify on first use — central Config management across spoke accounts
- [Amazon Security Lake](https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html) — to verify on first use — OCSF-normalized cross-account log aggregation
