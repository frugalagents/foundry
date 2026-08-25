---
type: platform-component
title: CMMC / CUI Compliance
description: platform design requirements for US defense contractors handling Controlled Unclassified Information — CMMC Level 2 boundary, NIST SP 800-171 controls, CUI repo classification, and FedRAMP-aligned stack
group: access
tags: [access, cmmc, cui, nist-800-171, defense-contractor, fedramp, dod, govcloud, controlled-unclassified]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [cmmc, cui, nist-800-171, defense-contractor, dod, dfars, fedramp, govcloud, controlled-unclassified, dib, defense-industrial-base]
decision-question: "Are you a US defense contractor or subcontractor in the Defense Industrial Base (DIB) who handles Controlled Unclassified Information (CUI) — technical data, export-controlled research, or sensitive government program information — requiring CMMC certification for DoD contracts?"
decision-domain: compliance_overlay
priority: 10
blocking: true
requires: [access/identity, exec/microvm]
---

CMMC (Cybersecurity Maturity Model Certification) is a DoD framework requiring
defense contractors to demonstrate compliance with cybersecurity standards as a
condition of contract award. For a coding agent platform, CMMC creates a specific
challenge: **the platform itself becomes part of the CMMC assessment boundary**
if it processes, stores, or transmits CUI.

CMMC Level 2 (required for most DoD contracts involving CUI) maps to NIST SP 800-171,
which has 110 security requirements across 14 control families. Several of these
directly constrain platform design choices.

> **Before designing:** Have your CMMC consultant or Registered Practitioner (RP)
> determine whether the coding agent platform falls within your CMMC assessment
> boundary. If developers use the platform to work on CUI-adjacent code, it is
> almost certainly in scope. Designing the platform outside the boundary and
> then having it pulled in during assessment is costly to remediate.

## CUI vs ITAR — The Key Distinction

These are different but overlapping categories:

| | CUI | ITAR |
|---|---|---|
| Governing framework | NIST SP 800-171 / CMMC | 22 CFR Parts 120–130 |
| Enforcement agency | DoD / DCSA | State Dept |
| Scope | Broad — any sensitive unclassified federal info | Specific — USML defense articles |
| Infrastructure requirement | FedRAMP Moderate minimum; GovCloud preferred | GovCloud required for most interpretations |
| Personnel restriction | US persons preferred; varies by contract | US persons mandatory |
| Overlap | ITAR-controlled technical data is also CUI | Some CUI is not ITAR |

A repo can be both CUI and ITAR-controlled. In that case, ITAR's stricter
requirements govern. See export-control.md for the ITAR-specific platform design.

## NIST SP 800-171 Controls Relevant to Platform Design

The 14 control families in NIST 800-171 that most directly affect the platform:

**3.1 — Access Control**
- Only authorized users access CUI-containing repos; enforce with IAM role
  scoping and repo classification checks at session init
- Limit platform functions available to CUI sessions (minimum necessary principle)
- Control remote access to the platform: VPN or PrivateLink only; no public
  internet endpoints for CUI-scoped sessions

**3.3 — Audit and Accountability**
- Log user activity on CUI-containing systems with sufficient detail to reconstruct events
- Protect audit logs from unauthorized access and modification (WORM storage)
- Retain audit logs for the period specified in your System Security Plan (SSP)
- Review audit logs for anomalous activity (→ security-ops.md)

**3.4 — Configuration Management**
- Establish and maintain a baseline configuration for the platform
- Track and control changes to the platform; maintain a configuration-controlled
  baseline (→ Terraform/CDK IaC for all platform configuration)
- Restrict, disable, or prevent the use of nonessential programs on CUI systems

**3.5 — Identification and Authentication**
- Identify users, processes, and devices before allowing access to CUI
- Authenticate with multi-factor authentication (MFA) for all CUI access
- Employ replay-resistant authentication (→ OIDC/SAML short-lived tokens,
  not long-lived API keys)

**3.12 — Security Assessment**
- Periodically assess the security controls in the platform to determine effectiveness
- Develop and implement plans of action to correct deficiencies
- Monitor the platform on an ongoing basis (→ GuardDuty, Security Hub)

**3.13 — System and Communications Protection**
- Implement subnetworks for publicly accessible system components separate from
  internal networks (→ VPC with private subnets for CUI processing)
- Employ FIPS-validated cryptography for CUI in transit and at rest
- Prevent unauthorized and unintended information transfer (→ VPC endpoints
  for AWS services; no traffic to internet from CUI subnets)

## Decisions

**What is the CMMC Level requirement?**
- Level 1 (17 practices) — basic cyber hygiene; no CUI involved; unlikely to
  apply to a coding agent platform deployment for DoD contracts
- Level 2 (110 practices = full NIST SP 800-171) — required for contracts
  involving CUI; most defense contractors fall here; the platform design in this
  node targets Level 2
- Level 3 (110 + NIST SP 800-172 subset) — enhanced requirements for highest
  priority programs; rare; requires government-led assessments; significant
  additional platform constraints beyond this node's scope

**Does the platform run in the CMMC boundary or outside it?**
- Inside the boundary — the platform processes CUI-containing code; it is in
  scope for CMMC assessment; every platform component (agent runtime, MCP gateway,
  model inference endpoint, log storage) must comply with NIST 800-171 controls;
  use FedRAMP Moderate or High authorized services only
- Outside the boundary with CUI data isolation — the platform runs in a standard
  commercial environment but CUI-tagged repos are blocked from agent access; the
  platform is not in scope because it never touches CUI; simpler compliance posture
  but severely limits platform utility for defense-adjacent engineering teams

**Which AWS environment satisfies the CMMC boundary?**
- AWS GovCloud (US) — FedRAMP High authorized; operated by US persons; strongest
  option; required if any ITAR-controlled CUI is involved; Bedrock available in
  GovCloud (verify current model availability)
- AWS commercial with FedRAMP Moderate services — acceptable for CMMC Level 2
  if your SSP documents the control implementation; Bedrock in commercial regions
  is FedRAMP Moderate authorized (verify current status); lower ops burden than
  GovCloud; suitable if ITAR is not in scope
- Consult your CMMC RP — the correct answer depends on your contract requirements
  and the sensitivity tier of the CUI involved; do not make this determination
  without a qualified CMMC advisor

**How are CUI repos classified and enforced?**
- SCM repo topic `cui-controlled` — GitHub Enterprise repo topic set by the
  program security officer; platform reads at session init; triggers CUI-mode
  access controls and enhanced logging; same pattern as ITAR classification
- CUI category tag — CUI has specific categories (CUI//SP-CTI for cyber threat
  intel, CUI//EXPT for export-controlled, CUI//PRVCY for privacy); tagging by
  category enables tiered access controls (some CUI categories are more sensitive
  than others)
- Static allowlist in SSP — if the number of CUI repos is small and stable,
  maintain a list in the System Security Plan; simpler, requires manual updates

**How is FIPS 140-2 cryptography enforced for CUI data in transit and at rest?**
- AWS FIPS endpoints — configure the platform to use FIPS-validated AWS API
  endpoints (e.g., `bedrock-runtime-fips.us-east-1.amazonaws.com`); ensures
  TLS using FIPS-validated cipher suites; required for 3.13 compliance
- S3 SSE-KMS with FIPS CMK — encrypt CUI-containing S3 objects and log buckets
  with a KMS Customer Managed Key using FIPS-validated key material; KMS is FIPS
  140-2 validated
- GovCloud automatically FIPS — GovCloud API endpoints are FIPS-validated by
  default; if on GovCloud, FIPS cryptography is satisfied at the infrastructure level

**How is MFA enforced for all CUI access?**
- IAM Identity Center with MFA policy — enforce MFA as a condition in the
  IAM Identity Center permission set; developers cannot assume the CUI-scoped
  IAM role without completing MFA; applies to all access regardless of network location
- Session tag for MFA completion — pass `mfa_authenticated=true` as a session tag
  from the IdP; IAM policy on the CUI Bedrock endpoint requires this tag; no MFA
  = no CUI inference access

**What is the audit log retention period?**
- NIST SP 800-171 does not specify a retention period — it requires retention
  "in accordance with organizational policy"; your SSP must specify the period;
  typical defense contractor SSPs specify 1-3 years; some contracts specify longer
- Apply S3 Object Lock with the SSP-specified retention period; document the
  retention decision and its basis in the SSP

## Principles

- The platform is a system in your CMMC boundary — treat it as such from the
  start; retrofitting CMMC controls onto a platform designed without them is
  expensive and disruptive; design for the boundary at the beginning
- Your System Security Plan is the living design document — every platform
  design decision that implements a NIST 800-171 control must be documented in
  the SSP; the SSP is what the C3PAO (CMMC Third Party Assessment Organization)
  reviews; an undocumented control is a gap in the assessment even if it is
  technically implemented
- CUI classification drives access, not vice versa — the access control system
  is only as good as the CUI classification; an unclassified CUI repo that the
  platform can freely access is a control failure; invest in classification
  accuracy before deploying the platform to defense teams
- FIPS is not optional for CUI — NIST SP 800-171 3.13.8 requires FIPS-validated
  cryptography; this is a hard requirement, not a best practice; any service
  in the CUI data path that does not use FIPS-validated crypto is a finding
- Plan for the C3PAO assessment — the assessment will review your SSP, interview
  platform engineers, and test controls; document everything; keep evidence
  (CloudTrail logs, IAM policy exports, encryption configuration screenshots)
  in a structured evidence repository

## Stack Options

**CMMC boundary infrastructure**
- AWS GovCloud (US-East/US-West) — FedRAMP High; FIPS endpoints by default;
  US-person operators; strongest CMMC posture; required if ITAR overlaps;
  Bedrock available (verify current model list in GovCloud)
- AWS commercial with FedRAMP Moderate — acceptable for CMMC Level 2 without
  ITAR overlap; use FIPS endpoint variants for all API calls; document FedRAMP
  authorization status of each service in the SSP; Bedrock, Lambda, ECS, S3,
  CloudWatch are all FedRAMP Moderate authorized (verify current status)

**Access control (3.1)**
- IAM Identity Center with MFA enforcement — MFA condition in permission set;
  session tags for MFA status; US-person status tag for CUI access gate;
  permission sets scoped to CUI-specific IAM roles with least-privilege policies
- AWS Organizations SCPs — deny access to non-FIPS endpoints; deny resource
  creation outside the approved region; enforce at the OU level for the CUI accounts

**Audit and accountability (3.3)**
- AWS CloudTrail — log all API calls in the CUI accounts; enable CloudTrail
  Insights for anomaly detection; cross-region trail for completeness; deliver
  to S3 with Object Lock; CloudTrail log file validation provides integrity check
- Amazon CloudWatch Logs — agent session events, tool calls, access events;
  log group resource policy restricts access to security role; export to S3
  for long-term retention per SSP retention period
- AWS Security Hub — aggregate findings from GuardDuty, Config, Inspector,
  Macie into a single security posture view; use CIS AWS Foundations Benchmark
  as a baseline; NIST SP 800-53 standard in Security Hub maps to 800-171 controls

**FIPS cryptography (3.13)**
- FIPS endpoint configuration — configure all AWS SDK clients with the FIPS
  endpoint variant; for Bedrock: `bedrock-runtime-fips.us-east-1.amazonaws.com`;
  for S3: `s3-fips.us-east-1.amazonaws.com`; maintain a list of FIPS endpoints
  for all services in the stack in the SSP
- AWS KMS with FIPS CMK — all encryption keys for CUI data use KMS CMKs
  with FIPS-validated key material; key policy restricts usage to authorized
  IAM roles; key rotation enabled

**CUI repo classification**
- GitHub Enterprise repo topics API — read `cui-controlled` and CUI category
  tags at session init; implement in the MCP gateway pre-flight check alongside
  ITAR check; same Lambda authorizer handles both classifications
- AWS Resource Groups tagging — if using CodeCommit, tag repos with
  `DataClassification=CUI` and specific CUI category; IAM tag-based policies
  enforce access control natively

**Configuration management (3.4)**
- Terraform / AWS CDK — all platform configuration declared as IaC; version-controlled;
  change-controlled through PR review; deployed via CI/CD pipeline; no manual
  console changes; drift detection via AWS Config; baseline configuration
  documented in SSP appendix
- AWS Config conformance pack — deploy NIST SP 800-171 conformance pack from
  AWS Config rules library; monitors for configuration drift against the NIST
  control baseline; findings reported to Security Hub

**System Security Plan documentation**
- AWS Artifact — download FedRAMP authorization packages for AWS services
  used in the platform; include as evidence in the SSP appendix; documents
  the AWS responsibility portion of each NIST 800-171 control
- SSP template — the CMMC community has published SSP templates aligned to
  NIST 800-171; use as the basis for the platform SSP; document each of the
  110 controls with implementation status and evidence pointer

## Connects to

- [Export Control (ITAR/EAR)](export-control.md) — ITAR-controlled repos are
  a subset of CUI; if a repo is both ITAR and CUI, ITAR's stricter GovCloud
  requirement governs; the two classification checks run in the same session-init
  pre-flight
- [Identity & Access](identity.md) — NIST 800-171 3.5 identification and
  authentication controls align with the platform's identity model; MFA enforcement
  and session tagging are identity-layer implementations of 800-171 requirements
- [Observability & Audit](../ops/observability.md) — NIST 800-171 3.3 audit
  requirements are the compliance driver for the audit trail design; the standard
  audit trail must meet 800-171 retention and integrity requirements for CUI accounts
- [Security Operations](security-ops.md) — NIST 800-171 3.6 incident response
  requires a documented incident response capability; security-ops.md provides
  the runbook structure; the CUI-specific incident response procedures must be
  in the SSP

## Sources

- [NIST SP 800-171 Rev 3](https://csrc.nist.gov/publications/detail/sp/800-171/3/final) — the authoritative 110-control standard; consult with CMMC RP for application to your specific contract
- [CMMC Model v2.0 — DoD](https://www.acq.osd.mil/cmmc/) — to verify on first use — Level 2 practice requirements; assessment guide
- [AWS CMMC compliance](https://aws.amazon.com/compliance/cmmc/) — to verify on first use — AWS responsibility matrices for NIST 800-171 controls; FedRAMP authorizations
- [AWS Config — NIST SP 800-171 conformance pack](https://docs.aws.amazon.com/config/latest/developerguide/operational-best-practices-for-nist-800-171.html) — to verify on first use — automated control monitoring rules
- [Amazon Bedrock — FedRAMP authorization](https://docs.aws.amazon.com/bedrock/latest/userguide/security-compliance.html) — to verify on first use — confirm current FedRAMP authorization level and GovCloud availability
