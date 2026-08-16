---
type: platform-component
title: SOX — Sarbanes-Oxley Compliance
description: platform design controls for Sarbanes-Oxley Section 302/404 compliance — change control for AI-assisted financial system code, segregation of duties, audit trail requirements, and the IT General Controls (ITGC) implications of a coding agent platform at public companies
group: access
tags: [access, sox, sarbanes-oxley, itgc, change-control, segregation-of-duties, financial-systems, public-company, audit, sec-reporting]
timestamp: 2026-08-15T00:00:00Z
status: candidate
traversal: conditional
trigger: [sox, sarbanes-oxley, itgc, change-control, segregation-of-duties, sox-compliance, financial-reporting-system, public-company, internal-controls, external-auditor]
decision-question: "Is the company a public company (or preparing to go public) subject to Sarbanes-Oxley, and does the coding agent platform touch code used in financial reporting systems, ERP integrations, revenue recognition logic, or other IT systems in scope for SOX IT General Controls?"
---

Sarbanes-Oxley (SOX) Section 404 requires public companies to assess and report
on the effectiveness of internal controls over financial reporting. For software
systems, this translates to IT General Controls (ITGCs) — the controls that govern
how code is developed, tested, approved, deployed, and monitored in systems that
affect financial reporting.

A coding agent platform creates two distinct SOX implications:

1. **The agent modifies code in SOX-scoped systems** — if the agent can write to
   repositories containing financial reporting logic (ERP integrations, revenue
   recognition, consolidation, SEC reporting pipelines), the agent becomes part
   of the ITGC change management control. The external auditor will ask: how do
   you ensure AI-generated code changes went through the same approval process
   as human-written changes?

2. **The platform itself may be a SOX-scoped IT system** — if the coding agent
   platform controls access to financial system source code, the platform's access
   controls and audit logs may be reviewed as part of the ITGC assessment. The
   auditor will ask: who can access what, and can you prove it?

> **Before designing:** Brief the internal audit and IT risk teams on the platform
> before any SOX-scoped deployment. They will determine which repos are in SOX
> scope and what ITGC evidence the external auditor requires. The platform team
> implements controls; internal audit defines the control requirements and provides
> auditor-acceptable evidence formats.

## SOX ITGC Control Families Relevant to Coding Agent Platforms

| ITGC Control Family | Traditional requirement | Coding agent implication |
|---|---|---|
| Change Management | All code changes documented, tested, approved, and reviewed before production | AI-generated code changes must follow the same change management process as human changes; no agent-direct-to-production path |
| Access Controls | Only authorized individuals can access and modify financial system code | Agent access to SOX-scoped repos must be controlled with the same rigor as human access; access reviews include agent-accessible repos |
| Segregation of Duties | Developer who writes code cannot also approve and deploy it | Agent-suggested code cannot be approved by the same developer who prompted it; SOD extends to the human-in-the-loop review step |
| Audit Trail | Complete, tamper-evident record of who changed what and when | Agent session logs for SOX-scoped repos must be WORM-retained and auditor-accessible; logs must show developer identity, not just service account |
| Incident Management | Security incidents affecting financial systems reported and remediated per defined process | Prompt injection or unexpected agent behavior on SOX-scoped repos must trigger the incident management process |

## Decisions

**How are SOX-scoped repos identified and tagged?**
- Internal audit maintains the SOX scope inventory — the internal audit team
  (not the platform team, not developers) maintains the list of IT systems and
  repos in SOX scope; repos are tagged `sox-scoped` in GitHub Enterprise topics
  by the internal audit team or their delegate; the platform reads this tag at
  session init; adding or removing the `sox-scoped` tag is an audited change
  requiring internal audit authorization
- Application control matrix integration — some enterprises maintain an Application
  Control Matrix that maps applications to SOX processes; the platform can query
  this system (typically a GRC tool like ServiceNow GRC or AuditBoard) via API
  at session init to determine whether any repo in the session is SOX-scoped;
  more authoritative than tag-based classification but requires GRC integration

**What change management controls apply to agent-suggested code on SOX-scoped repos?**
- Human review gate with documented approver identity — every agent-suggested change
  to a SOX-scoped file must be reviewed and approved by a named human reviewer
  who is different from the developer who prompted the agent; this is the
  segregation-of-duties control; GitHub branch protection enforces it: the PR
  requires approval from a member of the `sox-approvers` CODEOWNERS group, and
  the developer cannot self-approve
- Change ticket linkage — all code changes to SOX-scoped repos must reference a
  change management ticket (ServiceNow, Jira Service Management); the PR template
  for SOX-scoped repos includes a mandatory change ticket field; a GitHub Actions
  check validates the ticket number and confirms it is in an approved state before
  allowing merge; agent-suggested code that doesn't have an approved change ticket
  cannot be merged
- Testing evidence before merge — SOX change management typically requires documented
  test evidence (unit test results, UAT sign-off) before production deployment;
  the CI/CD pipeline for SOX-scoped repos must produce a test evidence artifact
  that is linked to the change ticket; agent-generated code that causes test
  failures must be remediated before the change can proceed

**How is segregation of duties enforced when an agent is in the loop?**
- The prompting developer cannot be the approver — this is the core SOD requirement
  in an AI-assisted change context; the developer who used the agent to generate
  the code is the "author"; the approver must be a different person; GitHub's
  required review + CODEOWNERS pattern enforces this technically; the PR author
  cannot dismiss their own required review
- Agent identity is not a person — the agent's contributions must be attributed
  to the developer who prompted them, not to a generic "AI" identity; the audit
  trail must show `developer_id=jsmith prompted agent; agent suggested change;
  jsmith committed; approved by mwilliams`; the external auditor needs to see
  human accountability at every step
- Four-eyes on model-generated changes — some external auditors will require
  two human approvers for agent-generated changes on the highest-risk SOX repos
  (revenue recognition, consolidation); confirm with internal audit whether
  two-approver requirement applies before deploying write access

**What audit trail evidence does the external auditor require?**
- Session log as ITGC evidence — for each agent session touching a SOX-scoped
  repo, the audit trail must show: developer identity (authenticated, not self-declared),
  repos accessed, files read and written, tool calls made, model invocations made,
  timestamp, session duration; this evidence is presented to the external auditor
  as ITGC evidence for the change management and access control assertions
- WORM retention for SOX scope — audit logs for SOX-scoped sessions must be stored
  in WORM-compliant storage (S3 Object Lock Compliance mode) for the SOX evidence
  retention period; typically 7 years (consistent with SEC record-keeping requirements);
  logs must be tamper-evident; the WORM configuration must be demonstrated to
  the auditor
- Auditor access without platform access — the external auditor needs to review
  session logs for SOX-scoped repos without having access to the production platform;
  provide a read-only IAM role scoped to the SOX-scoped audit log bucket; the
  auditor's access to the bucket is itself logged in CloudTrail; access is time-limited
  to the audit engagement period

**What access review controls apply to SOX-scoped repos?**
- Quarterly access reviews — SOX ITGC typically requires quarterly reviews of
  who has access to systems in financial reporting scope; the platform must provide
  a report of every developer who accessed a SOX-scoped repo in the quarter,
  including agent-mediated access; this report feeds the internal audit quarterly
  access review process
- Joiners/movers/leavers for SOX access — developers who leave the organization
  or change roles must have their agent platform access to SOX-scoped repos
  revoked immediately; this is typically handled through the IdP (Okta/Entra)
  deprovisioning flow, but the platform must verify that IdP deprovisioning
  translates to repo access removal
- Access certification for elevated permissions — developers with write access
  to SOX-scoped repos must certify their access need during the quarterly review;
  uncertified access is automatically revoked; the platform's access review report
  feeds the certification workflow in the GRC tool

**Does the platform itself require SOX ITGC assessment?**
- Yes, if the platform controls access to financial system code — if the platform
  is the mechanism by which developers access and modify financial system source
  code, the platform's access controls (who can log in, who can access which repos)
  are an ITGC that the external auditor will review; the platform team must provide
  evidence that: (1) access is role-based and reviewed, (2) audit logs are complete
  and tamper-evident, (3) the platform itself is patched and hardened per the
  organization's IT security policy
- Coordinate with the IT risk team — the IT risk team will determine whether the
  platform requires its own SOX ITGC assessment (i.e., is the platform itself
  a "relevant system" under the SOX scope assessment); this is common for platforms
  that touch financial system code

## Principles

- Agent-generated code follows human change management, not AI-special rules —
  there is no "AI exception" to SOX change management; code generated with the
  help of an agent must go through the same change ticket, testing, approval,
  and deployment process as any other code change; the agent is a development
  tool, not a change process bypass
- Developer accountability survives AI assistance — the external auditor needs
  to see a human name on every change; the developer who prompted the agent is
  accountable for the change; the audit trail must attribute the change to that
  developer, not to the agent or a generic AI service account
- Internal audit owns the SOX scope — the platform team must not determine which
  repos are in SOX scope; that determination belongs to internal audit (often with
  external auditor input); the platform implements the controls that internal audit
  specifies; scope creep or scope reduction requires internal audit sign-off
- Audit evidence must be auditor-ready before the audit — the external auditor
  arrives at a scheduled date; the evidence (session logs, access reviews, change
  records) must be in auditor-accessible format before that date; do not design
  a system where producing audit evidence requires the platform team to manually
  extract and transform data at audit time
- WORM is not optional for SOX scope — if internal audit has determined that the
  platform's session logs are ITGC evidence, those logs must be WORM-retained;
  a standard CloudWatch log group with a 90-day retention policy is not acceptable
  SOX evidence; design WORM storage into the architecture from day one

## Stack Options

**SOX-scoped repo tagging and enforcement**
- GitHub Enterprise topics + Lambda authorizer — internal audit sets `sox-scoped`
  topic; Lambda at session init reads topic via GitHub API; applies SOX-specific
  session policy (read-only by default for first deployment, write with mandatory
  review gate after internal audit approval)
- GitHub CODEOWNERS — `CODEOWNERS` file in SOX-scoped repos specifies the
  `sox-approvers` team as required reviewers for all file changes; GitHub enforces
  as a branch protection rule; the agent cannot bypass branch protection even
  if it has write access

**Change ticket linkage**
- GitHub Actions + ServiceNow integration — a GitHub Actions workflow checks
  for a `CHG-XXXXXX` pattern in the PR description; calls the ServiceNow API
  to validate that the change ticket exists, is approved, and includes the
  repo name; blocks merge if validation fails; the check result is logged as
  a GitHub status check (auditor-visible in the PR history)
- Jira issue + Jira Automation — same pattern using Jira Service Management;
  PR body must contain a Jira issue key; GitHub Actions calls the Jira API to
  confirm the issue is in the `Approved` status; Jira Automation can link the
  PR back to the issue for bi-directional traceability

**WORM audit log storage**
- S3 Object Lock Compliance mode — `aws s3api put-object-lock-configuration
  --bucket sox-audit-logs --object-lock-configuration
  '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Years":7}}}'`;
  no user (including root) can delete or modify objects within the retention period;
  demonstrated to external auditor via S3 bucket configuration screenshot and
  CloudTrail evidence of no delete events
- CloudWatch log group → Kinesis Firehose → S3 Object Lock — session logs
  flow from CloudWatch through Firehose to the WORM S3 bucket; Firehose delivers
  in batches every 60 seconds; once in S3 Object Lock, the logs are immutable;
  Firehose IAM role has `s3:PutObject` only (no delete permission)

**Quarterly access review report**
- S3 Athena query — session logs in S3 queried via Athena: `SELECT developer_id,
  repo_name, COUNT(*) as sessions, MIN(timestamp) as first_access,
  MAX(timestamp) as last_access FROM sox_sessions WHERE quarter='2026-Q3'
  GROUP BY developer_id, repo_name`; results exported to CSV for internal audit
- Amazon QuickSight SOX access dashboard — a dedicated QuickSight analysis
  accessible to internal audit showing developer access to SOX-scoped repos;
  filtered to the review period; accessible to the internal auditor via a
  time-limited QuickSight reader account

**Auditor-accessible evidence store**
- Read-only IAM role for external auditor — a named IAM role with `s3:GetObject`
  and `s3:ListBucket` on the SOX audit log bucket; no other permissions; assumed
  via temporary credentials (STS AssumeRole with 8-hour session); all access
  logged to CloudTrail; credentials provisioned by the IT risk team for the
  audit engagement period only

## Connects to

- [Legal Hold & E-Discovery](legal-hold.md) — SOX evidence retention requirements
  (7 years) and legal hold requirements may overlap for the same repos; the
  retention policy must satisfy both; legal hold adds chain-of-custody requirements
  that complement WORM storage
- [MNPI](mnpi.md) — financial system code at investment banks may be both SOX-scoped
  and MNPI-sensitive; session logs for these repos must satisfy both SOX WORM
  retention and MNPI metadata-only logging requirements; these requirements conflict
  (WORM wants everything; MNPI wants minimal content); legal and internal audit
  must resolve this in writing
- [Model Risk Management](model-risk-management.md) — financial institutions subject
  to SR 11-7 that also have SOX obligations must manage both MRM validation requirements
  and SOX change management requirements for the same repos; the human review gate
  (SOX SOD requirement) and the MRM human oversight requirement are often the same
  control — design it once and claim credit for both
- [Observability & Audit](../ops/observability.md) — the SOX-compliant audit trail
  is a specialized output of the observability pipeline; the session log schema
  must include all fields required for SOX ITGC evidence (developer identity,
  repos accessed, tool calls, timestamps)

## Sources

- [Sarbanes-Oxley Act Section 404 — Management Assessment of Internal Controls](https://www.sec.gov/rules/final/33-8238.htm) — consult internal audit and legal for application to AI coding tools
- [PCAOB AS 2201: An Audit of Internal Control Over Financial Reporting](https://pcaobus.org/Standards/Auditing/Pages/AS2201.aspx) — to verify on first use — PCAOB standard governing external auditor assessment of ITGC
- [COBIT 2019 — Change Management control objective](https://www.isaca.org/resources/cobit) — to verify on first use — control framework commonly used to structure ITGC; change management and access control domains most relevant
- [SEC Rule 17a-4 — electronic record retention](https://www.sec.gov/rules/final/34-38245.txt) — for broker-dealers subject to both SOX and SEC 17a-4 record-keeping requirements; WORM storage requirement source
