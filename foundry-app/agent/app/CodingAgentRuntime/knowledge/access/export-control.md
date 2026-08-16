---
type: platform-component
title: Export Control (ITAR / EAR)
description: access enforcement for ITAR and EAR controlled source code and firmware
group: access
tags: [access, itar, ear, export-control, us-government, compliance]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [itar, ear, export-control, defense-contractor, us-government, classified-code, encryption-source, hardware-firmware]
decision-question: "Do any repos contain ITAR or EAR controlled content — defense firmware, encryption source, hardware schematics — that legally cannot be processed by AI systems accessible to non-US persons?"
---

ITAR (International Traffic in Arms Regulations) and EAR (Export Administration
Regulations) are US federal regulations that restrict export of defense articles
and dual-use technologies. For a coding agent platform, the critical constraint
is this: **an AI model that processes ITAR-controlled source code must itself be
inaccessible to non-US persons**, and that inference must occur within a defined
ITAR boundary.

Getting this wrong is not a compliance gap — it is a federal violation. This node
surfaces the design requirements; the legal determination of what constitutes the
ITAR boundary for AI inference must come from your export control counsel, not
from the platform team.

> **Before designing:** Get written guidance from your export control counsel on
> two specific questions: (1) Does Amazon Bedrock in AWS GovCloud satisfy the ITAR
> boundary for AI processing of ITAR-controlled source code? (2) Does processing
> code in a Bedrock prompt constitute "export" under 22 CFR 120.17?
> Do not proceed with ITAR repo access until you have written answers to both.

## What ITAR/EAR Means for the Platform

**Repo classification is the foundation.** Every repository must be tagged with
its export control classification before the platform can enforce access rules:

| Classification | What it covers | Platform behaviour |
|---|---|---|
| ITAR (USML) | Defense articles, military networking hardware firmware, weapons-adjacent software | Inference in GovCloud only; US person check mandatory at session start; no non-US person access |
| EAR (ECCN 5D002 / 5E002) | Commercial encryption source code, dual-use networking software | US-region inference required; additional restrictions depend on specific ECCN and country of destination |
| EAR99 / Unrestricted | Standard commercial software with no export classification | Standard platform instance; no additional controls |

## Decisions

**What constitutes the ITAR boundary for inference?**
This is a legal question, not an engineering one. Possible positions your counsel
may take:
- AWS GovCloud (US) is within the ITAR boundary for AI inference — operators are
  US persons, data does not leave US sovereign territory
- Only on-premises inference within a COMSEC-controlled environment satisfies the
  boundary — rules out any cloud provider
- Depends on the specific USML category of the controlled item

**How is US person status verified at session time?**
- HR system integration — query an internal HR API or directory attribute
  (LDAP/SCIM attribute `usPersonStatus: true`) at session authentication;
  block session on ITAR-tagged repos if attribute is absent or false
- IAM role assignment — US-person engineers are members of an IAM group
  granted access to the ITAR instance; non-US persons are never provisioned
  into this group regardless of their team
- Manual attestation — developer self-certifies US person status at onboarding;
  recorded in the IdP as an attribute; weakest control, may not satisfy auditors

**How are repos classified and how does the platform read that classification?**
- SCM topic/tag — GitHub Enterprise repo topic `itar-controlled`; platform reads
  this tag via SCM API at session start; agent refuses to load the repo if the
  tag is present and the developer lacks US person status
- External classification service — a separate system-of-record for export
  classification; platform queries it via API; more authoritative, more
  infrastructure to maintain
- Static allowlist in platform config — list of ITAR repo names maintained by
  the platform team; simpler, requires manual updates when repos are added

**What happens when a session attempts to access a mixed repo?**
- Block the session entirely — safest; developer must use the ITAR instance
- Allow access to non-ITAR files only; block reads of ITAR-classified paths —
  complex to enforce correctly; risk of classification gaps
- Recommended: block the session and redirect to the ITAR instance; ambiguous
  partial-file enforcement is a liability, not a control

## Principles

- ITAR enforcement is a hard access control, not a guardrail — guardrails filter
  content; ITAR enforcement prevents access entirely; do not conflate them
- Repo classification must be maintained as code changes — a repo that starts
  as EAR99 and later has ITAR-controlled firmware added to it must be
  reclassified; the classification system needs a change-detection workflow
- The ITAR instance is physically and logically separate from the standard
  instance — shared components (IdP federation broker, observability aggregator)
  must not create a data path from ITAR-controlled repos to the standard instance
- Export control violations are criminal, not civil — escalate any ambiguity to
  counsel before deploying; the platform team does not make ITAR determinations

## Stack Options

**ITAR boundary infrastructure**
- AWS GovCloud (US-East / US-West) — physically located in US; operated by US
  persons; designed for ITAR/EAR workloads; subject to FedRAMP High; Bedrock is
  available in GovCloud for inference within the boundary; verify current model
  availability in GovCloud before committing
- On-premises inference (self-hosted model) — the only option if counsel rules
  out cloud providers entirely; Strands or LangChain on internal compute; highest
  ops burden; necessary for the most restrictive interpretations

**US person status check**
- Custom Lambda authorizer — at session authentication, the Lambda queries an
  internal HR API or LDAP attribute; returns allow/deny based on `usPersonStatus`;
  runs before any repo access is permitted; result cached per session token
- AWS IAM Identity Center attribute mapping — map the `usPersonStatus` LDAP
  attribute from Okta/Entra through to IAM Identity Center as a session tag;
  IAM policies on the ITAR Bedrock endpoint require the session tag; no Lambda
  required; cleaner but requires IdP attribute propagation to be working correctly

**Repo classification**
- GitHub Enterprise repo topics API — read `itar-controlled` and `ear-eccn-5d002`
  topics at session init via the GitHub API; implement in a session-start Lambda
  or MCP gateway pre-flight check; update topics when classification changes
- AWS Resource Groups tagging (for CodeCommit repos) — tag repos with
  `ExportControl=ITAR` using AWS resource tags; IAM policies enforce tag-based
  access control natively without custom code

**Audit trail for ITAR sessions**
- AWS CloudTrail in GovCloud — all API calls logged in-boundary; immutable;
  export to S3 in GovCloud for retention; do not replicate logs outside GovCloud
  boundary without counsel review
- S3 Object Lock (WORM) — apply WORM retention to ITAR session logs; log records
  cannot be deleted or modified; required retention period depends on your ITAR
  license conditions (typically 5 years)

## Connects to

- [Identity & Access](identity.md) — US person status is an identity attribute;
  the IdP must carry and propagate it; this node adds a pre-session verification
  step on top of standard identity checks
- [Observability & Audit](../ops/observability.md) — ITAR session logs require
  in-boundary retention and WORM storage; the standard observability pipeline
  must not route ITAR logs outside the GovCloud boundary
- [Security Posture](security-posture.md) — ITAR enforcement is part of the
  broader access control posture; prompt injection against ITAR-controlled code
  has federal liability implications beyond standard security risk
- [Guardrails & Policy](guardrails.md) — DLP rules must treat ITAR-tagged content
  as the highest classification tier; output filtering must prevent ITAR content
  from appearing in logs or responses routed outside the boundary

## Sources

- [AWS GovCloud (US) overview](https://aws.amazon.com/govcloud-us/) — to verify on first use — ITAR-eligible; operated by US persons; Bedrock availability to confirm
- [Amazon Bedrock in GovCloud](https://docs.aws.amazon.com/govcloud-us/latest/UserGuide/govcloud-bedrock.html) — to verify on first use — model availability and FedRAMP authorization status
- ITAR: 22 CFR Parts 120–130 (International Traffic in Arms Regulations) — consult export control counsel; do not interpret directly
- EAR: 15 CFR Parts 730–774 (Export Administration Regulations) — consult export control counsel
