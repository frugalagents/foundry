---
type: platform-component
title: MNPI — Material Non-Public Information
description: platform design controls for repos containing Material Non-Public Information — trading strategies, M&A code, client position management, and other information asymmetry-sensitive content at financial institutions
group: access
tags: [access, mnpi, material-nonpublic, trading-strategy, information-barriers, financial-ip, ma-code, insider-trading, securities-law]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [mnpi, material-nonpublic, trading-strategy, ma-code, financial-ip, information-barriers, insider-trading, securities-law, hedge-fund, investment-bank, trading-algorithm]
decision-question: "Do any repos contain code that, if read or processed by an AI system, could constitute access to Material Non-Public Information — trading strategies, pending M&A analysis code, client position management algorithms, or other content where AI processing creates information asymmetry or disclosure risk?"
decision-domain: compliance_overlay
priority: 10
blocking: true
requires: [access/identity, ops/observability]
---

Material Non-Public Information (MNPI) is information that is not available to
the general public and would be considered important to a reasonable investor
in making an investment decision. For financial institutions (investment banks,
hedge funds, asset managers, broker-dealers), MNPI creates specific platform
design obligations that are distinct from ITAR, HIPAA, and standard DLP:

- **Information barrier enforcement** — the firm's Chinese Wall separates teams
  with MNPI access (M&A, trading, research) from those without; an AI system
  that reads MNPI-containing code creates a potential barrier breach if the
  session data is accessible to individuals on the wrong side of the wall
- **Disclosure risk** — if AI session logs containing MNPI are subpoenaed in
  litigation, accessible to a vendor, or leaked, the firm faces potential securities
  law liability; the safest design minimizes what is logged
- **Insider trading risk** — an AI model that has processed MNPI in a prompt
  creates a theoretical risk: if the model's responses are influenced by that
  MNPI (e.g., recommending a trade, generating code that reflects MNPI), and
  those responses flow to a person who trades on them, the firm may have liability

> **Before designing:** Get a written determination from your legal and compliance
> team on two questions: (1) Does AI processing of MNPI-containing code constitute
> a "use" of MNPI under applicable securities law? (2) Do AI session logs containing
> MNPI create disclosure obligations or information barrier compliance issues?
> The platform team implements controls; legal defines the MNPI standard.

## MNPI vs Other Classifications

| Classification | Risk type | Primary control | Session logging |
|---|---|---|---|
| ITAR | Federal export violation | Hard access block; US-person gate | WORM, in-boundary |
| HIPAA PHI | Privacy / breach | DLP masking; BAA | 6-year WORM |
| Legal hold | Litigation evidence preservation | Write block; e-discovery logging | WORM, chain-of-custody |
| **MNPI** | Securities law / information barrier | Session log sequestration; metadata-only logging; information wall enforcement | Minimal; compliance-only access |
| Standard confidential | IP protection | Standard DLP | Standard audit trail |

The key difference: MNPI's primary control is **minimizing what is logged**, not
maximizing what is captured. For legal hold, you want comprehensive e-discovery
logs. For MNPI, you want the minimum necessary record — enough to demonstrate the
information barrier was maintained, not a full transcript that itself becomes
a liability.

## Decisions

**How are MNPI repos identified and classified?**
- Repo classification by legal/compliance — the compliance team (not developers,
  not the platform team) maintains the MNPI classification list; repos are tagged
  `mnpi-sensitive` in GitHub Enterprise topics by the compliance team; the platform
  reads this tag at session init; any change to the MNPI tag requires compliance
  team authorization
- Content-based classification (not recommended as sole mechanism) — Bedrock
  Guardrails or Macie scanning for patterns that might indicate MNPI content;
  useful as a secondary detection layer but not authoritative; a classifier that
  incorrectly identifies non-MNPI code as MNPI creates access friction; a classifier
  that misses real MNPI creates liability; human classification must be authoritative
- System-of-record classification service — some financial institutions run a
  dedicated information barrier management system (e.g., Actimize, Bloomberg AIM);
  the platform queries this system's API at session init for the repo's MNPI status;
  most authoritative source; requires integration with the existing system

**What session logging policy applies to MNPI sessions?**
- Metadata-only logging (recommended) — for sessions touching MNPI-tagged repos,
  log only: developer identity, session timestamp, repo names accessed, tool calls
  made (file path accessed, not content), session duration; do NOT log prompt content,
  model response content, or file content that was read; the audit record confirms
  who accessed the MNPI repo and when, without creating a transcript that is itself
  MNPI
- Full content logging with sequestration — log full session transcripts but route
  them to a sequestered log store accessible only to compliance officers and legal;
  never accessible to platform admins, management, or the developer themselves;
  higher compliance evidence value but the transcript is now a document that may
  be subject to privilege analysis or subpoena; legal must determine whether this
  is acceptable
- No logging at all (not recommended) — some institutions initially consider
  "don't log MNPI sessions" as the safest approach; this is incorrect; you still
  need an access log for information barrier compliance; metadata-only is the
  correct minimum

**How are information barriers enforced technically?**
- Role-based access with information wall check — at session init, a Lambda
  authorizer checks whether the developer's role (sourced from HR system claim)
  is on the correct side of the information wall for the MNPI repos in the session;
  if the developer's role and the MNPI repo's wall assignment are incompatible,
  the session is blocked with a clear message ("This repo is behind an information
  barrier — contact Compliance to request access")
- Separate MNPI platform instance — for firms where the information barrier
  requires complete technical separation (no shared infrastructure between sides
  of the wall), deploy a separate platform instance for the MNPI side; developers
  on the MNPI side use a different endpoint; cross-instance data flows are
  technically impossible
- Information wall attribute in IdP — the developer's information wall membership
  is an IdP attribute (e.g., `wall_side: research` or `wall_side: public`); this
  attribute flows through the federation chain as a session tag; the platform's
  repo access check compares the developer's wall side against the repo's wall
  classification; ensures wall enforcement is based on HR-managed identity,
  not developer self-declaration

**How is the MNPI classification maintained as code evolves?**
- Classification review trigger on significant repo changes — when a repo's
  content changes significantly (new module added, acquisition code merged),
  a GitHub Actions workflow creates a classification review ticket for the
  compliance team; the repo retains its current classification until compliance
  reviews and confirms or updates it
- Annual review by compliance — all MNPI-classified repos reviewed annually by
  the compliance team; reclassification events are logged with reviewer, date,
  and rationale

**What happens when a developer accidentally includes MNPI context in a prompt?**
- Bedrock Guardrails pattern detection — configure custom guardrail patterns
  for known MNPI identifiers (internal deal codenames, client identifier patterns,
  model parameter naming conventions); if detected in a prompt, block the inference
  call and log a compliance event; do NOT log the blocked prompt content in the
  standard audit trail (the prompt itself is MNPI)
- Developer notification and guidance — the developer receives a message: "This
  prompt appears to contain sensitive information. Please remove the highlighted
  content and retry."; no inference occurs; the platform does not retain the
  blocked prompt

## Principles

- Minimize the MNPI footprint in logs — every MNPI-containing log record is
  a potential liability; design the logging policy to capture the minimum necessary
  for compliance (access audit) without creating a discoverable record of the
  MNPI content itself
- Information barrier enforcement must be technically enforced, not policy-only —
  a policy that says "developers behind the wall should not use the public-side
  platform instance" is not an information barrier; the platform must technically
  prevent cross-wall access; IdP attributes and session-init checks are the mechanism
- The classification owner is compliance, not the platform team — the platform
  team implements the enforcement; the compliance team owns the classification list
  and the wall definitions; the platform team cannot determine what constitutes
  MNPI without compliance input
- MNPI classification changes are compliance events — adding or removing the
  `mnpi-sensitive` tag from a repo is not a developer-level action; it requires
  compliance authorization and is itself an audited event (who changed it, when,
  on whose instruction)
- Do not build a comprehensive MNPI audit trail without legal sign-off — a
  full-content MNPI session log is a double-edged sword; it may satisfy compliance
  auditors but creates a highly discoverable document in litigation; legal must
  explicitly sign off on what gets logged

## Stack Options

**MNPI classification enforcement**
- GitHub Enterprise repo topics + Lambda authorizer — compliance team sets
  `mnpi-sensitive` topic; Lambda at session init reads the topic via GitHub API;
  checks developer's `wall_side` session tag against repo's wall assignment;
  blocks or permits; logs the access decision to the compliance audit stream
- AWS Resource Tags + IAM tag-based policies — tag repos (or the S3 objects in
  the code index) with `MNPIClassification=Sensitive` and `WallSide=Research`;
  IAM policies on the code index bucket enforce wall-based access; enforced
  at the AWS layer without custom Lambda code

**Metadata-only session logging**
- Custom CloudWatch log filter — configure a subscription filter on MNPI session
  log groups that strips prompt and response content fields before forwarding
  to the central SIEM; keeps only metadata fields; the original unfiltered log
  is not stored (never written to S3)
- Lambda log processor — for structured JSON logs, a Lambda processes each log
  record and writes a metadata-only version to the compliance log bucket; the
  original record is discarded (never persisted); the Lambda's IAM policy has
  no S3 write permission for the full-content bucket

**Sequestered compliance log store**
- S3 bucket with IAM policy — bucket policy restricts `s3:GetObject` to
  `compliance-officer` IAM role only; platform admins and developers have no
  access; all access to the bucket is logged to CloudTrail; KMS CMK with key
  policy permitting decryption only by the compliance officer role
- AWS Lake Formation column-level security — if logs land in a data lake,
  Lake Formation enforces column-level access; compliance officers see all
  columns; all other roles see metadata columns only; sensitive content columns
  are hidden at the Lake Formation layer

**Information barrier attribute in IdP**
- Okta custom attribute `wall_side` — set by HR/compliance during provisioning;
  propagated through SAML/OIDC as a claim; mapped through IAM Identity Center
  as a session tag; IAM policies on MNPI repo access require matching session tag
- Automated provisioning via HR system SCIM — wall side assignment is managed
  in the HR system and pushed to Okta via SCIM; changes to wall assignment
  (when an employee moves from public-side to research-side or vice versa)
  propagate automatically to the IdP

**Blocked prompt handling**
- Bedrock Guardrails custom regex — define custom sensitive information type
  patterns for known MNPI markers; Guardrails applies in real time to every
  prompt; blocked prompts return a policy violation response; no inference occurs;
  no prompt content is retained by the platform

## Connects to

- [Legal Hold & E-Discovery](legal-hold.md) — MNPI repos that are also under
  litigation hold create a tension: legal hold requires comprehensive e-discovery
  logging; MNPI policy requires minimal logging; legal must resolve this tension
  in writing before the platform design is finalized for repos that are both
- [Model Risk Management](model-risk-management.md) — model-critical repos at
  investment banks are frequently also MNPI-classified (trading algorithm parameters,
  model outputs as MNPI); both designations apply simultaneously; the platform
  must handle both access controls and logging policies for the same repo
- [Guardrails & Policy](guardrails.md) — MNPI DLP rules are a specialized
  guardrail configuration; custom Bedrock Guardrails patterns for MNPI markers
  are the real-time enforcement mechanism
- [JupyterLab Surface](../surfaces/jupyterlab.md) — quant researchers working
  in JupyterLab frequently work with MNPI-adjacent code; the Jupyter surface
  must enforce MNPI session log sequestration and metadata-only logging for
  sessions touching MNPI-classified notebooks or imported modules

## Sources

- SEC Rule 10b-5 — general anti-fraud provision; insider trading prohibition; consult securities law counsel for application to AI systems processing MNPI
- [FINRA Rule 4511 — Books and Records](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4511) — to verify on first use — record-keeping requirements; may apply to AI session logs touching trading-related code
- [SEC guidance on information barriers (Chinese Walls)](https://www.sec.gov/tm/infobulletin5.htm) — to verify on first use — information barrier requirements for broker-dealers; application to AI systems requires counsel interpretation
