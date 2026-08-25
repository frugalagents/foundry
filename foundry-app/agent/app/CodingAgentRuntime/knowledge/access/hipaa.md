---
type: platform-component
title: HIPAA Compliance
description: platform design requirements for healthcare covered entities and business associates — PHI handling, BAA obligations, audit trail, and retention for AI interactions with healthcare codebases
group: access
tags: [access, hipaa, phi, healthcare, baa, covered-entity, business-associate, medical-device, ehr]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [hipaa, phi, healthcare, covered-entity, business-associate, ehr, medical-records, patient-data, hospital, health-insurance, medical-device-software]
decision-question: "Are you a HIPAA covered entity or business associate — a healthcare provider, health plan, healthcare clearinghouse, or a vendor whose software handles Protected Health Information — where AI interactions with codebases containing PHI create compliance obligations?"
decision-domain: compliance_overlay
priority: 10
blocking: true
requires: [access/identity]
---

HIPAA (Health Insurance Portability and Accountability Act) creates two distinct
obligations for a coding agent platform in healthcare contexts:

1. **PHI in the codebase** — many healthcare codebases contain PHI: test fixtures
   with real patient records, hardcoded patient IDs in legacy code, sample HL7/FHIR
   messages with real data. When the agent reads these files, it processes PHI.
   That processing is a HIPAA-regulated activity.

2. **The platform as a business associate** — if the platform processes PHI on
   behalf of a covered entity, the platform vendor (and the platform itself as an
   AWS-hosted system) is a business associate. A Business Associate Agreement (BAA)
   with AWS is required before PHI can be processed through any AWS service.

> **Before designing:** Confirm with your privacy counsel whether the coding agent
> platform qualifies as a business associate under your specific use case. The
> determination depends on whether the agent routinely accesses PHI as part of
> its function or only incidentally. Get this in writing. AWS offers a standard BAA
> for HIPAA-eligible services — ensure it is executed before any PHI touches
> the platform.

## What HIPAA Means for the Platform

| HIPAA requirement | Standard platform | HIPAA addition |
|---|---|---|
| Access control (§164.312(a)) | IAM roles, permission engine | Minimum necessary standard: agents access only the PHI-containing files needed for the task; no broad repo reads |
| Audit controls (§164.312(b)) | Tamper-evident session logs | Log every access to PHI-containing files with user identity, timestamp, file path; retain 6 years |
| Transmission security (§164.312(e)) | TLS in transit | FIPS 140-2 validated encryption for PHI in transit; VPC endpoints for AWS services to prevent PHI traversing public internet |
| PHI in AI prompts | Not addressed | PHI submitted in prompts is PHI the BA is processing; DLP must detect and either block or ensure it stays within the HIPAA-compliant boundary |
| Session log content | Standard audit fields | Session transcripts containing PHI are themselves PHI; apply BAA-covered retention and access controls to these logs |
| Breach notification | Incident response | Unauthorized AI access to PHI triggers HIPAA breach notification assessment (60-day notification window to HHS if confirmed breach) |

## The PHI-in-Code Problem

PHI is far more common in codebases than developers expect:

- **Test data fixtures**: unit test files with real patient records copied from
  production years ago; the most common source of PHI in non-prod code
- **Hardcoded sample data**: HL7 v2 messages, FHIR JSON examples, X12 EDI claim
  samples with real patient identifiers embedded in comments or test cases
- **Log snippets**: debug logs committed to the repo containing patient IDs,
  dates of service, or diagnosis codes
- **Database migration files**: SQL scripts with real patient data used during
  a migration that were committed and never cleaned up
- **Configuration files**: endpoints or identifiers that reference production
  PHI systems

The platform cannot assume PHI is absent from a healthcare codebase. Macie scanning
and DLP rules must be designed as if PHI is present unless proven otherwise.

## Decisions

**Is a BAA with AWS in place?**
This is a prerequisite, not a design decision. Without an executed BAA:
- No PHI may be processed through any AWS service
- Bedrock inference with PHI-containing prompts is prohibited
- Session logs containing PHI cannot be stored in CloudWatch or S3
- The platform cannot be deployed for HIPAA-regulated use cases

Bedrock is on AWS's list of HIPAA-eligible services (verify current status).
Execute the BAA before platform go-live for any HIPAA-regulated customer.

**How does the platform detect PHI in the codebase?**
- Amazon Macie pre-scan — run Macie on the S3-backed code index before the
  agent accesses it; Macie identifies S3 objects containing PHI (names, SSNs,
  dates of birth, medical record numbers, health plan beneficiary numbers);
  flag PHI-containing files in the code index with a PHI marker
- Bedrock Guardrails PII filter — configure a Guardrails policy that detects
  and masks/blocks PHI categories (HIPAA identifiers) in prompts and responses;
  acts as a real-time filter even if Macie didn't pre-flag the file
- Both together — Macie for batch pre-classification of the codebase; Guardrails
  for real-time prompt/response filtering; defence in depth

**What does the agent do when PHI is detected in a file it needs to read?**
- Block read and notify — safest; agent cannot read PHI-containing files;
  developer must remove PHI from test fixtures before agent access; creates
  developer friction but cleanest compliance posture
- Read with masking — agent reads the file but Guardrails masks PHI identifiers
  before they appear in the model context; agent works on masked content; masking
  quality is imperfect for complex PHI patterns; requires validation
- Read with audit escalation — agent reads the file, logs the PHI access event
  as a HIPAA audit record, notifies the privacy team; permitted for minimum-necessary
  access scenarios where the developer genuinely needs the agent to work with
  PHI-adjacent code; highest audit burden
- Recommended for test fixtures: block read + recommend developer replace with
  synthetic data (FHIR Synthea, or a de-identified dataset)

**How are session logs containing PHI handled?**
- PHI-tagged log stream — session logs from HIPAA-scoped repos are routed to a
  separate log stream tagged as PHI; this stream is stored in a BAA-covered S3
  bucket with 6-year retention (HIPAA §164.530(j)); access restricted to
  privacy officer and platform security team only
- Prompt/response content exclusion from standard logs — by default, prompt and
  response content is not logged in the standard audit trail for HIPAA-scoped
  sessions; only metadata (user identity, timestamp, file paths accessed, tool
  calls invoked) is logged in the standard stream; full content logging only
  when required for a security investigation, under the PHI-tagged stream rules

**How is PHI repo classification maintained?**
- Repo topic `hipaa-phi` — GitHub repo topic set by the privacy team; platform
  reads at session init; triggers HIPAA-mode logging and DLP guardrails
- Macie finding on S3 code index — Macie continuously scans the code index bucket;
  findings automatically tag the relevant S3 prefix as PHI-containing; platform
  picks up the tag at session init; dynamic (catches newly introduced PHI)
- Recommended: both — static topic for known PHI repos, Macie for dynamic detection

**What is the retention requirement for HIPAA audit logs?**
- 6 years from creation or last effective date — HIPAA §164.530(j) requires
  documentation of policies and activities to be retained 6 years; apply S3
  lifecycle rule to the PHI audit log bucket with a 6-year minimum retention;
  S3 Object Lock GOVERNANCE mode for protection against accidental deletion
  (COMPLIANCE mode if the organization requires stronger tamper-evidence)

## Principles

- PHI in code is PHI — a patient record in a unit test fixture has the same HIPAA
  status as a patient record in a production database; design the platform as if
  PHI is in the codebase from day one
- The BAA is the prerequisite gate — the platform does not go live for HIPAA use
  cases without an executed AWS BAA; this is not a risk acceptance, it is a
  legal requirement
- Minimum necessary is an architecture principle — the agent should access only
  the files required for the task; broad repository indexing for RAG must not
  ingest PHI-containing files without a specific minimum-necessary justification
- De-identification is the long-term fix — the correct resolution of PHI in test
  fixtures is replacing it with synthetic data (FHIR Synthea); the platform can
  accelerate this by flagging PHI-containing test files and recommending synthetic
  replacements; treat it as a code quality issue, not just a compliance issue
- Session logs containing PHI are themselves covered records — they inherit the
  same 6-year retention and access control requirements; do not treat them as
  standard ops logs

## Stack Options

**BAA and HIPAA-eligible services**
- AWS BAA — execute through the AWS console (Account settings → AWS Artifact);
  covers all HIPAA-eligible services including Bedrock, S3, CloudWatch, Lambda,
  RDS, DynamoDB, ECS, SageMaker; verify current eligible service list before
  designing the stack
- Amazon Bedrock — HIPAA-eligible inference endpoint (verify current status);
  model invocations with PHI stay within the BAA boundary; use VPC endpoint
  (`com.amazonaws.region.bedrock-runtime`) to prevent PHI traversing the public
  internet

**PHI detection**
- Amazon Macie — managed PHI/PII detection service; scans S3 objects; identifies
  HIPAA-defined identifiers (medical record numbers, health plan beneficiary
  numbers, certificate/license numbers); runs continuously; findings available
  via EventBridge for automated tagging workflows; configure custom data identifiers
  for organization-specific PHI formats (e.g., internal patient ID format)
- Amazon Bedrock Guardrails — configure PII filter with HIPAA identifier categories;
  applies to prompts and responses in real time; can mask, block, or anonymize
  detected PHI; combine with Macie for defence in depth

**PHI audit log storage**
- Amazon S3 with Object Lock (GOVERNANCE or COMPLIANCE mode) — 6-year retention;
  versioning enabled; access restricted by bucket policy to privacy officer IAM role
  and platform security role; server-side encryption with KMS CMK; CloudTrail
  logging on the bucket for access audit
- AWS CloudTrail Lake — immutable event store with SQL query; useful for HIPAA
  audit because the privacy officer can query access events directly; restrict
  access to the CloudTrail Lake data store via resource-based policy

**Synthetic test data (recommended advisory)**
- FHIR Synthea (open source) — generates realistic synthetic patient data in
  FHIR R4 format; no real PHI; use to replace real-patient test fixtures;
  recommend as part of the platform's code quality suggestions for HIPAA repos
- AWS HealthLake — if the organization uses HealthLake, it provides de-identified
  dataset export; use de-identified exports for test fixtures rather than
  production-sourced data

**Breach notification workflow**
- Amazon EventBridge + SNS — trigger on Macie high-severity PHI finding or
  Guardrails PHI block event; publish to SNS topic subscribed by privacy officer
  and CISO; 60-day HIPAA breach notification clock starts at discovery; having
  an automated alert means the clock starts reliably

## Connects to

- [Security Posture](security-posture.md) — prompt injection targeting PHI-containing
  repos has HIPAA breach implications beyond standard security risk; the threat
  model for HIPAA repos must include HIPAA breach as an impact category
- [Guardrails & Policy](guardrails.md) — HIPAA DLP rules are a specialized guardrail
  configuration; PHI identifier categories in Bedrock Guardrails are the real-time
  enforcement mechanism
- [Observability & Audit](../ops/observability.md) — PHI audit logs are a separate
  log stream with different retention, access controls, and legal status from
  standard ops logs; the observability pipeline must route them separately
- [Legal Hold & E-Discovery](legal-hold.md) — HIPAA breach investigations may
  trigger litigation hold obligations; the intersection of HIPAA audit logs and
  legal hold requirements requires both WORM storage and legal hold tagging

## Sources

- [AWS HIPAA compliance](https://aws.amazon.com/compliance/hipaa-compliance/) — HIPAA-eligible services list; BAA execution process
- [Amazon Bedrock — HIPAA eligibility](https://docs.aws.amazon.com/bedrock/latest/userguide/security-compliance.html) — to verify on first use — confirm Bedrock is on the current HIPAA-eligible services list
- [Amazon Macie — HIPAA identifiers](https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html) — to verify on first use — managed data identifier list including HIPAA-defined PHI categories
- [HIPAA §164.312 — Technical safeguards](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html) — consult privacy counsel for application to AI systems
- FHIR Synthea synthetic patient generator — https://synthea.mitre.org/ — open source; generates realistic de-identified FHIR data for test fixtures
