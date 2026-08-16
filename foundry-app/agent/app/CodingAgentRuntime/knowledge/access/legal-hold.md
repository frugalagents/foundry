---
type: platform-component
title: Legal Hold & E-Discovery
description: read-only enforcement and e-discovery-grade logging for repos under litigation hold
group: access
tags: [access, legal-hold, e-discovery, litigation, compliance, worm]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [litigation-hold, e-discovery, legal-hold, active-litigation, patent-litigation, repo-freeze]
decision-question: "Are any repos or codebases under active litigation hold — requiring write blocking, e-discovery-grade session logging, and retention override for all AI interactions?"
---

A litigation hold (legal hold) is a directive from legal counsel requiring an
organization to preserve all information potentially relevant to anticipated or
active litigation. For a coding agent platform, this creates two distinct
requirements that must both be satisfied:

1. **Write blocking** — the agent must not modify any file in a held repo;
   no commits, no branch creation, no refactoring, no test generation that
   touches held files
2. **E-discovery-grade logging** — every AI interaction with a held repo must
   be logged as potential discoverable material, with chain-of-custody and
   tamper-evidence properties that would satisfy a court's evidence standards

These are not the same as standard guardrails and observability. Standard logs
are sufficient for SOC 2. E-discovery has different requirements: admissibility,
chain of custody, tamper-evidence beyond standard immutability, legal hold
notification, and preservation obligations that override normal retention
policies.

> **Before designing:** Have your legal team specify what "e-discovery grade"
> means for AI session logs in the context of your specific litigation. The
> technical controls here are implementable — but the standard they need to meet
> is a legal determination, not a platform team decision. Get the spec in writing
> before building the logging pipeline.

## What Legal Hold Means for the Platform

| Requirement | Standard platform | Legal hold addition |
|---|---|---|
| Write access | Controlled by permission engine | Hard block on all writes to held repos — not configurable, not overridable by developer |
| Session logging | Tamper-evident audit trail | E-discovery-grade: WORM storage, chain of custody, legal hold tag, preservation beyond normal retention |
| Retention | Per compliance policy (e.g., 13 months) | Indefinite hold until legal counsel releases — cannot be deleted by automated retention policies |
| Access notification | Not required | Legal and platform team notified when any session accesses a held repo |
| Scope | Per-session | Must capture: developer identity, timestamp, every file read, every prompt involving held content, every model response |

## Decisions

**How does the platform know a repo is under legal hold?**
- Legal hold registry — a platform-maintained list of held repos with hold start
  date and legal matter identifier; updated by the platform team on legal
  counsel's instruction; agent reads this at session start
- SCM topic/tag — GitHub repo topic `legal-hold`; platform reads at session
  init; simpler but requires SCM access to be reliable; topic changes must be
  immediate when holds are placed or released
- External legal hold management system — some enterprises run dedicated legal
  hold platforms (Relativity, ZL Technologies); integrate via API if available;
  most authoritative source

**What exactly is blocked?**
- All writes — no file edits, no new files, no deletes, no branch creation,
  no commits, no PRs; read operations permitted; agent can read and explain
  held code but cannot touch it
- All writes plus read notification — every read from a held repo generates a
  notification event; useful when legal team needs to know the held content
  was accessed; adds log volume

**How are e-discovery logs structured?**
This requires legal team input. Common requirements:
- Complete session transcript: every prompt, every tool call involving held files,
  every model response that includes held content
- Developer identity with non-repudiation: not just a user ID, but a verifiable
  identity chain (IdP session token, MFA confirmation)
- Timestamp precision and synchronization: logs must use a trusted time source
- Tamper-evidence: WORM storage with cryptographic integrity check; any
  modification attempt must be detectable
- Legal hold identifier on every log record: ties the log to the specific matter

**What triggers a hold release?**
- Written instruction from legal counsel only — never automated; never
  developer-initiated; platform team acts on instruction; release date logged
- Hold release is itself an auditable event: who released it, when, on whose
  instruction

## Principles

- Write blocking on held repos is not a guardrail configuration — it is a
  hard permission denial at the registry level; the agent must be incapable
  of writing, not just discouraged; implement as a registry allowlist entry with
  write operations removed
- E-discovery logs are not a substitute for — and must be separate from —
  your standard audit trail; they have different retention, different access
  controls, and different legal status
- Normal log retention policies must not apply to legal hold logs; automate
  a hold-override so that retention deletion jobs skip records tagged with
  a legal hold identifier
- Access to legal hold logs must itself be access-controlled: only legal
  counsel and designated IT custodians should be able to read the e-discovery
  log store; platform admins should not have standing read access
- Placing a repo under hold and releasing a repo from hold are both auditable
  events — log who performed each action, when, and on whose instruction

## Stack Options

**Write blocking**
- Registry allowlist entry — remove write tools (file edit, git commit, branch
  create) from the allowed tool set for held repos; implemented as a repo-scoped
  permission override in the MCP gateway; agent simply has no write tools
  available when a held repo is in context
- GitHub branch protection rules — set the held repo's default and all branches
  to require PR review and disable force push; even if the agent somehow
  generates a commit, it cannot push; defence-in-depth alongside the registry
  block
- AWS CodeCommit repository policy — if using CodeCommit, apply an S3-style
  bucket policy denying `PutFile` and `CreateBranch` actions for the agent's
  IAM role on held repos

**E-discovery-grade logging**
- Amazon S3 Object Lock (WORM mode) — apply COMPLIANCE mode (not GOVERNANCE
  mode) Object Lock to the e-discovery log bucket; COMPLIANCE mode cannot be
  overridden even by root; set retention period to indefinite (maximum allowed)
  until legal releases the hold; this is the strongest tamper-evidence control
  AWS provides
- AWS CloudTrail Lake — immutable event store with SQL query capability;
  useful for e-discovery because legal teams can query it directly; apply
  resource-based policies to restrict access to legal custodians only
- Amazon Macie on the e-discovery log bucket — continuously scans for sensitive
  content; alerts if log records are unexpectedly modified or if PII appears in
  logs that should not contain it
- Cryptographic log chaining — each log record includes the hash of the previous
  record (blockchain-style); any gap or modification breaks the chain; implement
  as a Lambda that appends records to a DynamoDB table with a previous-hash
  attribute; hash chain is the chain-of-custody proof

**Legal hold notification**
- Amazon EventBridge rule — trigger on any MCP gateway tool call where the
  repo matches the legal hold registry; publish a notification event to an SNS
  topic subscribed by the legal team and platform admins
- AWS Security Hub custom finding — create a custom finding type for legal hold
  access events; integrates with your existing Security Hub workflow and
  ticketing system

**Hold registry**
- AWS Systems Manager Parameter Store — store the held repo list as a versioned
  parameter; the platform reads it at session init; each version change is
  automatically logged with timestamp and IAM identity of who changed it;
  provides an audit trail of when holds were placed and released

## Connects to

- [Registry / Catalog](../registry/registry.md) — write tool removal for held
  repos is a registry-level operation; the hold status drives a tool permission
  override
- [Permission Engine](../harness/perms.md) — write blocking is enforced at the
  permission layer; held repos get a repo-scoped deny-write rule regardless of
  the developer's normal permissions
- [Observability & Audit](../ops/observability.md) — e-discovery logs are a
  separate log stream from the standard audit trail; the observability pipeline
  must route held-repo session events to the WORM store, not just the standard
  SIEM
- [Security Operations](security-ops.md) — accessing a held repo must generate
  an alert; the incident response process for litigation hold violations (e.g.,
  a write that somehow succeeded) needs to be pre-defined

## Sources

- [Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) — to verify on first use — COMPLIANCE mode WORM; non-overridable retention; chain-of-custody properties
- [AWS CloudTrail Lake](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html) — to verify on first use — immutable event store with SQL query; access-restricted; suitable for e-discovery production
- Federal Rules of Civil Procedure Rule 37(e) — electronically stored information preservation obligations; consult legal counsel for application to AI session logs
