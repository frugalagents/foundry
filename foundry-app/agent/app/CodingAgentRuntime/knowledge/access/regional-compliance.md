---
type: platform-component
title: Regional Compliance & Works Council
description: platform design constraints imposed by EU works councils, GDPR employee monitoring rules, and co-determination requirements in specific jurisdictions
group: access
tags: [access, regional-compliance, works-council, gdpr, co-determination, germany, eu, employee-monitoring, betriebsrat]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [works-council, betriebsrat, gdpr, eu-deployment, germany, co-determination, employee-monitoring, european-offices, employee-data-processing]
decision-question: "Do you have engineering teams in jurisdictions with employee monitoring co-determination requirements — specifically Germany (Betriebsrat), the Netherlands (Ondernemingsraad), or France (CSE) — where the works council must approve platform design choices before deployment?"
decision-domain: compliance_overlay
priority: 9
blocking: true
requires: [ops/observability]
---

In several EU jurisdictions — most significantly Germany — deploying a coding agent
platform that logs developer activity is a co-determination matter requiring works
council (Betriebsrat) approval **before** deployment. This is not a legal risk to
be managed after the fact: deployment without works council agreement is unlawful
and reversible by the works council.

The works council's concern is not whether you deploy an AI coding assistant. It is
whether the platform can be used to monitor, evaluate, or performance-manage
individual developers. The platform design choices below directly determine how
difficult works council approval will be and how long it takes.

> **Before designing the EU deployment:** Engage employment law counsel and the
> local works council early — ideally during design, not at deployment. The platform
> team cannot determine what constitutes "performance monitoring" under applicable
> co-determination law; that determination belongs to counsel and the works council.
> Present the platform design to the works council as a collaborative process, not
> an IT announcement.

## What Co-Determination Requires

The key distinction is **individual** vs **aggregate** data:

| Data type | Works council position (typical) | Platform design implication |
|---|---|---|
| Individual session logs (who wrote what, when) | Restricted or prohibited for performance evaluation | Do not surface individual metrics in management dashboards |
| Individual token consumption | Typically requires works council agreement if used for evaluation | Aggregate at team level for cost dashboards; individual view for the developer only |
| Aggregate team/BU usage metrics | Generally permissible | Safe for operations and cost reporting |
| AI-generated code diff per developer | Restricted if linked to performance | Do not generate per-developer productivity reports |
| Session recordings or keystroke logs | Typically prohibited | Do not implement; not required for platform operation |
| Anonymized quality/adoption metrics | Generally permissible | Safe for platform health dashboards |

## Decisions

**What is the scope of works council consultation?**

This is a legal determination, not an engineering one. Your employment law counsel
will assess which of the following applies under the specific jurisdiction:

- Full co-determination right (§87 BetrVG in Germany) — works council has a
  genuine veto; deployment cannot proceed without agreement; negotiate a
  Betriebsvereinbarung (works council agreement) that specifies permitted uses,
  data retention, and access controls
- Information and consultation right — works council must be informed and consulted
  before deployment; they cannot veto but must have adequate input time
- No co-determination right — jurisdiction does not require works council involvement
  for this type of tooling; proceed with standard GDPR data minimization obligations

**How is individual vs aggregate data enforced at the platform level?**
- Attribution model: team-level only — cost and usage metrics are attributed at the
  team or squad level, never at the individual developer level; the platform does not
  store a `developer_id` → `session_cost` mapping accessible to management; only
  the developer can see their own session data
- Attribution model: individual with access controls — individual session data is
  stored but access-controlled so that only the developer and the security team (for
  incident investigation) can read it; management dashboards show only aggregates;
  requires a Betriebsvereinbarung clause specifying these access controls explicitly
- Attribution model: individual unrestricted — do not use in German or Dutch
  deployments; will not pass works council review

**What does the Betriebsvereinbarung (works council agreement) need to specify?**

The platform team must provide a technical annex to the agreement specifying:
- Exactly what data is logged per session (list of fields with data types and
  retention periods)
- Who has access to which data and under what circumstances
- That AI-generated metrics are not used in performance evaluation processes
- The process for a developer to request deletion of their own session data (GDPR
  Art. 17 right to erasure — subject to legitimate retention overrides)
- The process for the works council to audit platform compliance annually

**How is GDPR data minimization enforced for session logs?**
- Log only what is necessary for the stated purpose — operations (errors, latency),
  security (tool call audit, access events), and cost attribution; do not log full
  session transcripts by default; prompt/response content is the highest-sensitivity
  field; log it only for security investigation purposes with strict access controls
- Purpose limitation enforcement — each log stream is tagged with its legal basis
  and processing purpose; automated controls prevent cross-purpose data use (e.g.,
  security logs cannot feed an HR analytics pipeline)
- Retention alignment — retention periods declared in the Betriebsvereinbarung must
  be technically enforced; EventBridge Scheduler + Lambda deletion job or S3 lifecycle
  rules must be in place and auditable

**What is the deployment sequence to get works council approval?**
1. Engage employment law counsel → get jurisdiction-specific assessment
2. Draft platform design document specifying all data collected, retention, access
3. Present to works council for consultation (Germany: Betriebsrat typically needs
   4–6 weeks minimum for complex IT systems)
4. Negotiate Betriebsvereinbarung terms — works council will propose restrictions;
   evaluate which are technically feasible; design the platform to satisfy them
5. Obtain signed Betriebsvereinbarung before deploying to German-sited developers
6. Document the agreement in the platform runbook; audit annually

**How is per-developer data handled for the developer themselves?**
- Developer self-service access — the developer can query their own session history,
  token usage, and cost; this is GDPR-compliant (Art. 15 right of access) and
  typically acceptable to works councils because it gives the developer control
- Opt-out of personalization features — if the platform includes org-knowledge
  pattern mining (aggregate learning from developer sessions), provide an opt-out
  mechanism; works councils will require it; implement before deployment not after

## Principles

- Design for works council approval, not for minimal compliance — a platform
  designed to just barely pass review creates friction in every future feature;
  design the attribution and logging model to be works-council-friendly from the
  start; it makes the platform easier to explain and approve
- Individual developer data is not a management tool — the platform generates
  data that could be misused for performance monitoring; the platform team must
  actively prevent that misuse through technical controls, not just policy
- The Betriebsvereinbarung is a design document — treat it as a binding technical
  specification; every data collection and access control decision must be
  traceable to a clause in the agreement
- Works council engagement is an early dependency, not a gate at the end —
  presenting a finished platform to the works council for approval is the
  wrong sequence; co-design the data model with their requirements in mind
- GDPR obligations apply regardless of works council — even in jurisdictions
  without co-determination requirements, GDPR data minimization, purpose limitation,
  and retention obligations apply to all EU developer data

## Stack Options

**Attribution model enforcement**
- CloudWatch custom metrics with team-level dimensions only — define CloudWatch
  metrics with `team` and `business_unit` dimensions; do not include `developer_id`
  as a metric dimension; individual data exists in logs but is not surfaced in
  dashboards; team-level QuickSight dashboard safe for management reporting
- DynamoDB with access-controlled individual records — store individual session
  data in DynamoDB with a condition expression requiring `requesting_user == session_owner`
  for reads; management role has no `GetItem` permission on individual records;
  enforced by IAM policy, not application logic

**GDPR retention enforcement**
- S3 lifecycle rules — define lifecycle rules per log bucket matching the retention
  period declared in the Betriebsvereinbarung; automatic deletion; auditable via
  S3 Lifecycle configuration history; tested with S3 Lifecycle dry-run before deployment
- EventBridge Scheduler + Lambda deletion job — for DynamoDB or structured stores;
  schedule a Lambda to delete records older than the agreed retention period; log
  every deletion run to CloudTrail for audit; send run summary to platform ops SNS topic
- AWS Backup with retention policies — for structured data stores that need point-in-time
  recovery within the retention window but hard deletion after it

**Purpose limitation**
- Log stream tagging by purpose — tag each CloudWatch log group with the processing
  purpose (`security-audit`, `cost-attribution`, `operations`); IAM resource policies
  restrict cross-purpose access; security team cannot read cost logs; finance cannot
  read security audit logs
- Lake Formation column-level security — if session logs land in a data lake, Lake
  Formation enforces column-level access by IAM role; security team sees full session
  fields; cost team sees only cost fields; developer identity fields masked for
  management roles

**Developer self-service access (GDPR Art. 15)**
- Lambda-backed API — developer invokes a personal data API that returns all log
  records where `developer_id` matches their own session token; deployed as an
  internal API Gateway endpoint; IAM auth ensures developers can only retrieve
  their own data
- Automated GDPR erasure request handler — Step Functions workflow triggered by
  a developer erasure request; identifies all records for the developer across
  log stores; deletes or anonymizes subject to retention overrides (legal hold,
  security incident); sends completion confirmation to developer

**Works council audit**
- Annual read access for works council representative — a named IAM role with
  time-limited read access to the compliance log stream (not full session transcripts);
  activated by the platform team on works council request; deactivated after audit;
  all access logged to CloudTrail

## Connects to

- [Identity & Access](identity.md) — jurisdiction routing uses the `country_iso`
  claim from the IdP broker; EU developers are routed to EU-region instances with
  regional compliance controls active
- [Data Jurisdiction](data-jurisdiction.md) — works council data minimization
  requirements intersect with data residency requirements; EU developer session
  logs must stay in EU regions; data-jurisdiction.md covers the residency
  enforcement mechanism
- [Observability & Audit](../ops/observability.md) — the standard audit pipeline
  must be modified for EU deployments to enforce purpose limitation and retention;
  log routing rules separate compliance-controlled streams from standard ops streams
- [Progressive Trust](progressive-trust.md) — trust signal accumulation (session
  quality metrics per developer) must be handled carefully in EU jurisdictions;
  if trust signals are used in access decisions, they may constitute automated
  decision-making subject to GDPR Art. 22

## Sources

- [§87 Betriebsverfassungsgesetz (BetrVG) — co-determination in technical monitoring](https://www.gesetze-im-internet.de/betrvg/__87.html) — consult employment law counsel; do not interpret directly for platform design
- [GDPR Art. 88 — processing in the context of employment](https://gdpr-info.eu/art-88-gdpr/) — employee data processing under national implementing legislation
- [German Federal Data Protection Act (BDSG) §26 — data processing for employment purposes](https://www.gesetze-im-internet.de/bdsg_2018/__26.html) — to verify on first use with counsel
- [AWS GDPR data processing addendum](https://aws.amazon.com/compliance/gdpr-center/) — AWS contractual basis for EU data processing
