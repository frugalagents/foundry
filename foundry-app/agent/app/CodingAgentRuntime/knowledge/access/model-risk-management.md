---
type: platform-component
title: Model Risk Management (SR 11-7)
description: OCC/Federal Reserve guidance on model risk management as it applies to AI coding agent platforms in financial institutions — validation scope, MRM team engagement, ongoing monitoring, and documentation requirements
group: access
tags: [access, model-risk, sr-11-7, occ, mrm, financial-services, model-validation, ai-governance, fed-guidance]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [sr-11-7, model-risk, mrm, occ-guidance, fed-guidance, financial-model-validation, ai-validation, model-risk-management, banking-regulation, quantitative-model]
decision-question: "Are you a financial institution subject to SR 11-7 (OCC/Federal Reserve model risk management guidance), and does your coding agent platform touch code used in quantitative models, risk systems, credit decisioning, or other model-driven financial processes?"
decision-domain: compliance_overlay
priority: 9
blocking: true
requires: [quality/evals, ops/observability]
---

SR 11-7 is the Federal Reserve's supervisory guidance on model risk management
(published 2011, with subsequent OCC bulletins). It requires financial institutions
to have a disciplined framework for identifying, validating, and monitoring models
used in financial decision-making. In 2011 this meant quantitative pricing models
and credit scorecards. In 2026 it increasingly applies to AI systems — including
AI coding tools that generate code for those models.

The central question for a coding agent platform: **does the agent qualify as a
"model" under SR 11-7, and if so, what validation and monitoring does that require?**

This determination belongs to the institution's Model Risk Management (MRM) team,
not the platform team. The platform team's job is to engage MRM early, provide
them with the information they need to make the determination, and implement the
controls they specify.

> **Before designing:** Brief the MRM team on the platform before any code is
> written. Provide: (1) a description of how the agent generates outputs (model
> invocation, tool calls, code generation); (2) which business processes it touches
> (code for pricing models, risk models, credit decisioning); (3) how outputs are
> used (developer accepts/rejects suggestions vs agent writes directly to production).
> MRM's determination will scope the validation work. Do not assume the agent is
> out of scope — that assumption is frequently wrong.

## SR 11-7 Definition of "Model"

SR 11-7 defines a model as a quantitative method, system, or approach that:
1. Applies statistical, economic, financial, or mathematical theories to transform
   inputs into quantitative estimates
2. The outputs are used to guide a consequential decision

A coding agent that generates code for a risk model, pricing engine, or credit
scorecard arguably satisfies this definition — especially if:
- Developer acceptance rates are high (the agent's output is used with minimal human modification)
- The code it generates directly implements financial logic (not just boilerplate)
- The agent has access to model parameters, training data, or model architecture decisions

**When MRM is likely to determine the agent IS in scope:**
- The agent writes code that is deployed directly into a production risk model, pricing engine, or credit scoring system
- The agent's code generation is used with minimal human review for model-critical paths
- The agent has access to proprietary model logic, training data, or backtesting results

**When MRM may determine the agent is NOT in scope (or lower priority):**
- The agent only assists with infrastructure code (CI/CD, tooling, tests) for model systems
- A human expert reviews and validates every agent suggestion before any model code changes
- The agent is used only for code explanation and documentation, never for generating model logic

## What the Platform Team Must Provide to MRM

Before MRM can scope the validation, the platform team must document:

| Document | Content | Maintained by |
|---|---|---|
| Model inventory entry | Name, description, inputs (developer prompt + codebase context), outputs (code suggestions), use cases | Platform team |
| Output usage description | How outputs are used — does the developer accept/reject/modify, or does the agent commit directly? | Platform team |
| Scope of code access | Which repos can the agent access? Which contain model-critical code? | Platform team + repo owners |
| Human oversight controls | What guardrails, review requirements, and approval gates are in place? | Platform team |
| Audit trail description | What is logged per session? How long retained? Who can access? | Platform team |

## Decisions

**What does MRM validation of a coding agent typically require?**

MRM validation scope varies by institution. Common requirements:

- **Conceptual soundness review** — documentation of the LLM's training approach,
  known limitations (hallucination, domain gaps), and how these limitations are
  mitigated by the platform design (guardrails, human review gates, domain capability evaluation)
- **Outcome analysis** — empirical testing of agent output quality on a sample of
  tasks in scope; what is the error rate? what types of errors occur? are errors
  detectable by the reviewing developer?
- **Human oversight assessment** — evaluation of whether the human-in-the-loop
  controls are sufficient to catch agent errors before they reach production models
- **Ongoing monitoring plan** — specification of what metrics will be tracked
  post-deployment to detect model degradation or drift (e.g., developer correction
  rate, rollback frequency, defect rate in model code)

**How does the platform team support ongoing MRM monitoring?**
- Session quality metrics for MRM — in addition to standard ops metrics, export
  a model-risk-specific metric stream: developer acceptance rate per repo category,
  rate of manual overrides of agent suggestions on model-critical repos, rollback
  events on model repos; delivered to MRM team's monitoring dashboard
- Periodic validation refresh — MRM will typically require a validation refresh
  when the underlying model changes significantly (e.g., Claude Sonnet → Claude Opus
  or a major version update); platform team must notify MRM before upgrading the
  model version for populations using the agent on model-critical code
- Incident reporting to MRM — any platform incident (prompt injection, unexpected
  output pattern, model hallucination that reached production) affecting model-critical
  code must be reported to MRM within the institution's model incident reporting SLA

**How is the human oversight requirement implemented technically?**
- Mandatory human review gate on model-critical repos — repos tagged `model-critical`
  require every agent-suggested change to go through a named human expert review
  (not just a generic PR approval); the CI/CD pipeline enforces that the PR has
  a review from a member of the `model-validators` GitHub team before merge
- Read-only mode for initial deployment — for the first validation period (typically
  3-6 months), the agent operates in read-only + suggestion mode only on model-critical
  repos; no direct writes; every suggestion is presented to the developer as a proposal;
  the developer types the accepted code manually or approves a diff; this maximizes
  human oversight during the validation window
- Audit trail for MRM access — MRM team members have a named IAM role with read
  access to session logs for model-critical repo interactions; this role is time-limited
  and activated on request; all MRM audit log access is itself logged

**What is the escalation path when a model is updated?**
- Pre-update notification to MRM — the platform team notifies MRM at least 30 days
  before upgrading the underlying LLM version for populations using the agent on
  model-critical code; MRM determines whether re-validation is required
- Change log maintained by platform team — a running log of all model version
  changes, significant configuration changes (guardrail updates, repo access scope
  changes), and material platform incidents; provided to MRM at each periodic review

## Principles

- MRM determination is not the platform team's to make — the platform team
  provides information and implements controls; MRM determines scope and validation
  requirements; never assume out-of-scope without a written MRM determination
- The more autonomous the agent, the more likely MRM scope expands — an agent
  that generates and commits model code without human review is a higher-risk
  model than one that proposes suggestions a developer must explicitly accept;
  design for maximum human oversight on model-critical paths, especially early
- Human review gates are both a compliance control and a validation mechanism —
  requiring expert review of agent suggestions on model-critical code serves
  double duty: it satisfies the "human oversight" requirement and generates
  outcome data (how often does the expert modify or reject the suggestion?) that
  feeds the ongoing monitoring program
- Model versioning must be governed — an LLM model version upgrade is a model
  change under SR 11-7; treat it with the same change management discipline as
  a quantitative model parameter update; do not upgrade silently
- Document everything — the SR 11-7 validation file is a living document;
  every design decision that affects the agent's behavior on model-critical
  code must be documented with a rationale; "we decided not to enable direct
  writes on pricing model repos because..." is valuable validation evidence

## Stack Options

**Model inventory and documentation**
- Confluence / SharePoint MRM model inventory — most institutions have an existing
  model inventory system; add the coding agent as a model entry with the required
  fields; link to the platform documentation in the entry
- AWS Systems Manager Parameter Store — store the model inventory entry as a
  versioned parameter; version history provides a change log; readable by the
  MRM team via a cross-account IAM role

**Human review gate enforcement**
- GitHub branch protection rules — require review from `model-validators` CODEOWNERS
  group for changes to model-critical paths; enforced at the SCM layer independent
  of the agent; the agent cannot bypass branch protection even if it has write access
- GitHub Actions check — a CI check that verifies every PR touching a `model-critical`
  tagged repo has a qualifying review; blocks merge if review is from the same developer
  who made the change (no self-review on model code)

**MRM monitoring metrics**
- CloudWatch custom metrics — `ModelCriticalAcceptanceRate` (% of agent suggestions
  accepted without modification on model-critical repos), `ModelCriticalRollbackRate`
  (rollbacks on model-critical repos), `ModelCriticalOverrideRate` (% of suggestions
  manually modified before acceptance); these feed the ongoing monitoring dashboard
- Amazon QuickSight MRM dashboard — separate dashboard accessible to MRM team;
  shows monitoring metrics trended over time; model version change dates marked
  as annotations on the trend charts

**Pre-update notification workflow**
- AWS Step Functions with 30-day timer — when a model version upgrade is planned,
  create a Step Functions execution that waits 30 days before permitting the
  upgrade; notification sent to MRM SNS topic at execution start; MRM responds
  via approval workflow; upgrade proceeds only on approval
- GitHub issue template — lower-tech alternative; create a GitHub issue from a
  template for each planned model upgrade; MRM reviews and closes the issue to
  approve; GitHub Actions checks for a closed MRM approval issue before allowing
  the model version parameter change

## Connects to

- [Guardrails & Policy](guardrails.md) — the guardrails configuration for
  model-critical repos (restricted tool access, suggestion-only mode) is the
  technical implementation of MRM's human oversight requirement
- [Observability & Audit](../ops/observability.md) — the MRM monitoring metrics
  are a specialized output of the observability pipeline; the standard audit trail
  must be exportable to MRM's monitoring system
- [Model Capability Evaluation](../quality/model-capability-eval.md) — the
  capability evaluation framework provides the empirical evidence that MRM's
  conceptual soundness review requires; run the capability evaluation on
  model-critical code domains and share the results with MRM as validation evidence
- [MNPI](mnpi.md) — model-critical repos at investment banks frequently also
  contain MNPI (trading strategy code, pricing algorithm parameters); the repo
  classification system must handle both designations simultaneously

## Sources

- [Federal Reserve SR 11-7: Supervisory Guidance on Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) — consult with compliance counsel for application to AI systems; do not interpret directly
- [OCC Bulletin 2011-12: Sound Practices for Model Risk Management](https://www.occ.gov/news-issuances/bulletins/2011/bulletin-2011-12.html) — companion guidance to SR 11-7
- [OCC Bulletin 2021-38: Model Risk Management Principles for Banks Using AI](https://www.occ.gov/news-issuances/bulletins/2021/bulletin-2021-38.html) — to verify on first use — OCC guidance specifically addressing AI model risk; published 2021; most directly applicable
