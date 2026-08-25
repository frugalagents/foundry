---
type: platform-component
title: Data Jurisdiction & Sovereignty
description: enforcing data residency, cross-border transfer restrictions, and sovereignty boundaries for developer session data and code processed by the agent
group: access
tags: [access, data-jurisdiction, data-residency, sovereignty, china, eu, gdpr, cross-border, schrems, transfer-impact]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [data-residency, data-jurisdiction, china-deployment, eu-data-residency, sovereignty, cross-border-transfer, schrems2, transfer-impact-assessment, regulatory-data-boundary, mlps, pipl]
decision-question: "Do you have regulatory, contractual, or sovereign requirements that restrict where developer session data or processed source code can be stored, transmitted, or inferred — particularly for China, EU, or other jurisdictions with strict cross-border transfer rules?"
decision-domain: compliance_overlay
priority: 10
blocking: true
requires: [access/identity, ops/federation]
conflicts_with: [access/export-control]
---

Data jurisdiction is the set of rules governing where data can be processed, stored,
and transmitted. For a coding agent platform, the relevant data includes: source
code submitted in prompts, session transcripts (prompt + response), developer
identity data, and inferred outputs. Each of these may be subject to different
jurisdictional constraints depending on where the developer is located, what the
code contains, and what the applicable regulations require.

The hardest cases arise when two jurisdiction requirements conflict:

- **ITAR (US) + China sovereignty**: ITAR-controlled source code cannot leave
  US-controlled infrastructure; Chinese PIPL/MLPS requires certain data to remain
  in China. The same piece of code cannot satisfy both requirements simultaneously.
  The correct answer is two separate platform instances with no data path between them.

- **EU GDPR residency + global team access**: EU developer identity data must be
  processed under GDPR adequacy or appropriate safeguards; if the platform is
  US-hosted, a valid transfer mechanism (SCCs + TIA) is required for EU developer
  personal data flowing to the US inference endpoint.

> **Before designing:** Identify every jurisdiction your developers are located in.
> For each jurisdiction, get a legal determination of what data (if any) is subject
> to residency or transfer restrictions. This is a legal analysis, not an engineering
> estimate. Incorrect assumptions here can result in regulatory enforcement.

## Jurisdiction × Data Matrix

Map your developer locations and code classification against jurisdiction requirements
before selecting a platform topology:

| Developer location | Data type | Key regulations | Platform implication |
|---|---|---|---|
| China (mainland) | Developer session data, code | PIPL, MLPS Level 2+ | Must be processed on infrastructure in China; no cross-border transfer without consent/approval |
| EU/EEA | Developer personal data (identity, session metadata) | GDPR | Transfer to US requires SCCs + TIA or adequacy decision; EU-region instance preferred |
| Germany specifically | Session logs, usage metrics | GDPR + BetrVG | See regional-compliance.md |
| US (ITAR-controlled code) | Defense firmware, USML content | ITAR 22 CFR | Must stay within GovCloud; see export-control.md |
| Japan | Developer personal data | APPI | Adequacy decision with EU; transfers to US require safeguards; less restrictive than GDPR |
| India | Developer personal data | DPDPA 2023 | Data localization requirements for certain categories; consult counsel for applicability |
| Unrestricted | Standard commercial code | No residency requirement | Standard platform instance |

## Decisions

**Which jurisdictions require a dedicated platform instance?**
- China deployment — mainland China requires a dedicated instance hosted on
  Chinese cloud infrastructure (Alibaba Cloud, Tencent Cloud, or AWS China operated
  by SINNET/GCL); no data path to the global platform instance; Chinese PIPL
  prohibits transfer of personal data outside China without user consent, government
  approval, or a Standard Contract; the platform team must assess MLPS level
  requirements for the specific deployment
- ITAR-controlled deployment — separate GovCloud instance (see export-control.md);
  no data path to the China instance or the global commercial instance
- EU regional instance — recommended (not always legally required) to simplify
  GDPR compliance; hosting in eu-west-1 or eu-central-1 eliminates cross-border
  transfer concerns for EU developer personal data; if cost constraints prevent a
  dedicated EU instance, document the transfer mechanism (SCCs + TIA) instead

**For instances that do serve cross-border traffic, what is the valid transfer mechanism?**
- AWS Data Processing Addendum (DPA) + Standard Contractual Clauses (SCCs) —
  AWS's DPA includes SCCs; sufficient for EU → US transfer for AWS-processed data;
  you must still complete a Transfer Impact Assessment (TIA) evaluating US
  surveillance law risk for your specific data categories
- AWS GovCloud as adequacy substitute — GovCloud's operator and data access controls
  are relevant to the TIA; may reduce TIA risk profile; does not replace SCCs
- EU-US Data Privacy Framework (DPF) adequacy decision — as of 2024, the DPF
  provides an adequacy mechanism for EU → US transfers to DPF-certified companies;
  verify AWS's current DPF certification status; note that DPF has been legally
  challenged previously; maintain SCCs as a backup

**How is data residency enforced technically?**
- AWS Region lock via SCP — an AWS Organizations SCP denies `ec2:RunInstances`,
  `s3:CreateBucket`, `rds:CreateDBInstance`, etc. outside the approved region(s);
  developers and platform automation cannot create resources in non-approved regions;
  the SCP is the technical enforcement of the residency commitment
- S3 bucket policy with `aws:RequestedRegion` condition — prevents objects from
  being replicated or copied to non-approved regions; defence-in-depth alongside
  the SCP
- Bedrock endpoint VPC binding — invoke Bedrock only through a VPC endpoint in the
  approved region; Lambda or ECS agent code is configured with the regional endpoint;
  cross-region inference profiles must be reviewed against residency requirements
  before enabling (they route to different AWS regions)

**How is China instance isolation maintained?**
- No shared components — the China instance has its own: IdP connection (China
  tenant), MCP gateway, model endpoint (Chinese LLM provider or approved model),
  observability stack, and billing; the only shared element is the platform code
  (deployed separately); treat it as a different customer environment
- Chinese LLM providers — Bedrock is not available in AWS China regions; use a
  China-licensed model provider (Baidu ERNIE, Tongyi Qianwen/Alibaba, Zhipu AI,
  or a self-hosted open-weight model); LiteLLM or similar unified gateway abstracts
  the provider difference from agent code
- MLPS filing — operating a cloud service in China at MLPS Level 2 or above requires
  filing with the Ministry of Public Security; your Chinese cloud provider handles
  the infrastructure-level MLPS compliance; the platform team's responsibility is
  ensuring the application-level controls meet the specified MLPS level

**How is developer jurisdiction determined at session time?**
- IdP claim (`country_iso`) — the identity broker normalizes country from the
  upstream IdP; session routing uses this claim to direct developers to the correct
  regional instance; requires accurate country data in the upstream IdP
- IP geolocation (fallback only) — use as a secondary check; not authoritative for
  compliance purposes; a VPN-using developer in China appearing as US should not
  bypass China-instance routing; IdP claim is authoritative
- Explicit instance selection (for dual-jurisdiction developers) — developers who
  regularly work across jurisdictions (e.g., a US person assigned to a China project)
  need a clear policy for which instance they use; the default is: use the instance
  for the jurisdiction where the code's data subject/residency requirements apply,
  not the developer's physical location

## Principles

- Conflicting jurisdiction requirements resolve to separate instances, not clever
  shared-instance design — there is no technical solution that allows ITAR-controlled
  code and China-resident data to coexist in one platform instance; the correct answer
  is isolation, not complexity
- Data residency commitments must be technically enforced, not just documented —
  a policy statement that "EU data stays in EU" means nothing if an engineer can
  create an S3 bucket in us-east-1 and copy data there; SCPs are the technical
  enforcement mechanism; the commitment is only real if the SCP is in place
- Cross-region inference profiles require a residency review — Bedrock cross-region
  inference profiles improve availability by routing to secondary regions; if a
  secondary region is outside the residency boundary, the profile must be disabled
  or restricted; check this before enabling for any jurisdiction-constrained instance
- The China instance is not a subset of the global platform — it is a parallel
  deployment with its own governance, its own model provider, and its own compliance
  requirements; resource it and operate it accordingly
- Transfer Impact Assessments are a one-time design effort, not an ongoing burden —
  document the TIA for each data flow at design time; review it when laws change
  or when the data flow topology changes; do not repeat from scratch each year

## Stack Options

**Data residency enforcement (AWS)**
- AWS Organizations SCP — `Deny` on all resource-creation actions outside approved
  regions; applied at the OU level for the platform accounts; no exceptions for
  platform engineers; the boundary is the SCP, not trust
- Amazon Macie — scans S3 buckets for unexpected PII and flags objects in buckets
  outside the approved region; compensating detective control alongside the SCP

**China instance**
- AWS China (Beijing/Ningxia) — operated by SINNET (Beijing) and GCL (Ningxia);
  separate AWS account, separate credentials, separate console login; Bedrock not
  available; use LiteLLM + China LLM provider API (Baidu ERNIE via API, Alibaba
  Tongyi via DashScope API, or self-hosted Qwen)
- Alibaba Cloud (alternative) — mature enterprise offering in China; Function Compute
  (serverless) for agent execution; PAI (Platform for AI) for model hosting; Object
  Storage Service (OSS) for log retention; native integration with Alibaba's LLMs
- Self-hosted open-weight model on Chinese cloud compute — for highest data
  sensitivity; deploy Qwen, DeepSeek, or similar on GPU instances; inference stays
  entirely within the Chinese cloud boundary; highest ops burden

**EU instance / transfer mechanism**
- Bedrock in eu-west-1 / eu-central-1 — inference stays in EU; no cross-border
  transfer of prompt data; simplest residency solution
- AWS SCCs via DPA — for EU → US flows that are unavoidable; AWS's DPA includes
  SCCs; supplement with a Transfer Impact Assessment document; store the TIA with
  the platform compliance documentation
- Amazon CloudFront with geo-restriction — prevent EU-instance API endpoints from
  being accessed from outside EU; defence-in-depth ensuring EU developers stay on
  the EU instance

**Session routing by jurisdiction**
- Amazon API Gateway with Lambda authorizer — authorizer reads `country_iso` claim
  from the JWT; returns the correct regional endpoint URL; agent client connects to
  the returned endpoint; jurisdiction routing happens transparently at auth time
- Route 53 latency-based + geolocation routing — pair with the Lambda authorizer;
  geolocation routing as a network-layer complement; not sufficient alone (VPNs
  bypass it); use as latency optimization, not as compliance enforcement

## Connects to

- [Export Control (ITAR/EAR)](export-control.md) — the hardest data jurisdiction
  conflict: ITAR requires GovCloud boundary; China PIPL requires China boundary;
  these cannot be the same instance; see export-control.md for the ITAR-specific
  controls
- [Regional Compliance](regional-compliance.md) — GDPR data minimization and
  purpose limitation apply to EU developer data regardless of where it is processed;
  residency is a necessary but not sufficient condition for GDPR compliance
- [Identity & Access](identity.md) — jurisdiction routing depends on accurate
  `country_iso` claims from the IdP broker; IdP federation chain must propagate
  this attribute reliably
- [Multi-Cloud Governance](../ops/multi-cloud-governance.md) — China and EU
  instances may run on different cloud providers; multi-cloud governance provides
  the policy-as-code overlay that maintains consistent guardrails across providers
- [Observability & Audit](../ops/observability.md) — log export must respect
  residency boundaries; China instance logs cannot be shipped to a global SIEM
  hosted in the US; each jurisdictional instance needs a local-first logging path

## Sources

- [China PIPL (Personal Information Protection Law)](http://www.npc.gov.cn/npc/c30834/202108/a8c4e3672c74491a80b53a172bb753fe.shtml) — consult China data protection counsel before designing China deployment
- [China MLPS (Multi-Level Protection Scheme) overview](https://www.china-briefing.com/news/chinas-cybersecurity-multi-level-protection-scheme-mlps-2-0/) — to verify on first use; MLPS level determines compliance obligations
- [GDPR SCCs (Standard Contractual Clauses) — EC implementing decision 2021/914](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32021D0914) — EU → third country transfer mechanism
- [AWS China region — service availability](https://www.amazonaws.cn/en/about-aws/regional-product-services/) — to verify on first use — Bedrock not currently available in AWS China
- [Amazon Bedrock — available regions](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-regions.html) — to verify on first use — confirm EU region model availability
