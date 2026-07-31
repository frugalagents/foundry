# Platform Advisor Moat System Design

**Status:** Proposed target architecture  
**Date:** 2026-07-28  
**Working name:** Architecture Decision Assurance System  
**Moat:** Architecture Outcome Network

## 1. Thesis

Do not compete with Claude or ChatGPT on architecture prose.

Build a system that can answer:

> For enterprises with these constraints, which platform designs were feasible,
> which design was selected, what was actually implemented, what changed during
> delivery, and what measurable outcomes and failures followed?

Frontier models can summarize public patterns. They do not have a governed,
longitudinal record linking enterprise context, alternatives, decisions,
implementations, controls, costs, incidents, and outcomes.

The product should therefore move from a **questionnaire that generates a
blueprint** to a **living architecture decision and assurance workspace**.

## 2. Honest Assessment Of V2

### Keep

The current v2 engine has the right foundation:

- A typed, deterministic kernel with no LLM decision authority.
- Critical evidence gates that withhold decision-grade outputs.
- Workload-specific discovery and sizing inputs.
- Versioned rules, catalogs, traces, and human overrides.
- A separation between architecture decisions and narrative generation.
- A pure engine that can be replayed and tested.

These features make the output more auditable than an ordinary chat response.

### Why It Is Not Yet A Moat

The active decision system is still straightforward to reproduce:

- Three operating models are selected primarily from three ownership fields.
- Thirteen hand-authored components are activated through conditionals.
- Provider-neutral components contain only AWS service mappings.
- V2 presents one answer rather than feasible alternatives and trade-offs.
- Evidence is user-entered data, not verified claims linked to source artifacts.
- Controls are prose, not executable policies or conformance tests.
- Any matching control can reduce residual risk without proof of effectiveness.
- Cost uses fixed component prices and coarse multipliers.
- Current tests prove determinism and contracts, not architectural correctness.
- Sessions store generated state, not the architecture decision lifecycle.
- There is no record of actual implementation, cost, incidents, or later outcomes.

Determinism makes current judgment consistent. It does not make that judgment
proprietary or proven.

## 3. Product Wedge

Start with one high-value decision:

> **Pre-production decision assurance for regulated, multi-tenant enterprise
> agent-hosting platforms.**

The first release compares exactly three implementation families under the same
requirements:

1. AWS-managed.
2. Portable open source on Kubernetes.
3. Hybrid managed and portable.

Azure, GCP, and additional SaaS providers enter through the same adapter contract
after the method is proven. The architecture must support them from day one, but
the initial catalog should favor depth over nominal breadth.

The product promise is not "we generate your architecture." It is:

> We inspect your proposed platform, identify missing evidence, compare feasible
> alternatives, and prove whether the selected design satisfies workload,
> isolation, policy, reliability, operability, portability, and cost requirements.

## 4. Target System

```text
Enterprise artifacts and architect input
                   |
                   v
       1. Evidence and claim plane
                   |
                   v
  2. Requirements and capability ontology
                   |
                   v
  3. Hard-constraint feasibility engine
                   |
                   v
  4. Provider adapter and bundle generator
                   |
                   v
  5. Pareto ranking and outcome evidence
                   |
                   v
  6. ADR, controls, tests, estimate, backlog
                   |
                   v
  7. Review, implementation, and drift loop
                   |
                   v
       8. Architecture Outcome Network
```

### 4.1 Evidence And Claim Plane

Ingest:

- Architecture diagrams and ADRs.
- Terraform, CloudFormation, CDK, and Kubernetes manifests.
- IAM, OPA, Cedar, network, and data-access policies.
- Cloud inventory, quotas, support plans, and service eligibility.
- Bills, pricing assumptions, model usage, latency, and availability data.
- Security standards, regulatory obligations, and operating-model documents.
- Representative agent traces and evaluation results.

Agents may extract candidate claims, but architects approve decision-critical
claims. Each claim is immutable and includes:

```text
claim_id
subject, predicate, object
source_id, source_location, content_hash
tenant_id, owner, reviewer
observed_at, retrieved_at, valid_from, valid_to
extractor_version, confidence, approval_status
```

The engine should expose contradictions and stale claims instead of silently
choosing one.

### 4.2 Provider-Neutral Ontology

Keep these layers independent:

- **Context:** workload, audience, scale, autonomy, impact, data, regulation.
- **Organization:** decision rights, funding, delivery, operations, incidents.
- **Requirements:** hard constraints, SLOs, controls, economic limits.
- **Capabilities:** identity, runtime, policy, gateway, memory, registry,
  evaluation, observability, audit, delivery, isolation, resilience, metering.
- **Topology:** control plane, runtime placement, trust boundaries, regions.
- **Implementation offerings:** products or projects that realize capabilities.
- **Bundles:** mutually compatible offerings forming an implementable platform.
- **Outcomes:** delivery, reliability, governance, cost, adoption, and failures.

The core relationship chain is:

```text
EvidenceClaim -> Requirement -> Capability -> CandidateBundle
    -> Tradeoff -> DecisionRecord -> ControlTest
    -> ImplementationInstance -> OutcomeObservation
```

Architecture rules operate only on context, requirements, capabilities, and
topology. Provider adapters must never create or weaken architecture requirements.

### 4.3 Provider Adapter Contract

Replace `ComponentDecision.aws_services` as the primary model with:

```text
CapabilityDecision
  id, scope, requirements, dependencies, required_controls

ImplementationOffering
  provider, product, version, capabilities
  regions, deployment_models, isolation_models
  identity_protocols, telemetry_protocols, policy_interfaces
  compliance_assertions, quotas, maturity, support
  license, portability, operational_burden
  prices, source_assertions, freshness

ImplementationDecision
  capability_id, offering_id, configuration
  satisfied_constraints, rejected_constraints
  cost_range, effort_range, evidence_snapshot
```

Initial adapters:

- `aws-managed`
- `kubernetes-oss`
- `hybrid`

Later adapters:

- `azure-managed`
- `gcp-managed`
- `saas`

Every provider fact must include provenance, region, version, retrieval date,
content hash, reviewer state, and expiry policy. Stale facts can lower a ranking;
stale compliance or availability facts must block a hard decision.

### 4.4 Decision And Assurance Engine

Use a hybrid system:

1. Validate evidence and contradictions.
2. Derive hard requirements, controls, and SLOs.
3. Derive provider-neutral operating model and topology.
4. Compute required capability and dependency closure.
5. Ask adapters for eligible offerings.
6. Generate compatible implementation bundles.
7. Eliminate bundles that violate hard constraints.
8. Calculate risk only from verified control coverage and effectiveness.
9. Return the Pareto frontier across:
   - security and compliance;
   - reliability;
   - delivery time;
   - cost;
   - operational burden;
   - portability and reversibility;
   - existing skills and estate fit.
10. Rank viable alternatives using declared customer priorities and comparable
    outcome evidence.
11. Abstain or require expert review outside validated coverage.

Do not collapse all uncertainty into one confidence number. Report:

- Evidence completeness.
- Evidence freshness.
- Hard-constraint satisfaction.
- Recommendation stability under sensitivity analysis.
- Comparable-case sample size and outcome range.
- Expert-review requirement.

Return one of four states:

- `decision_ready`
- `conditional`
- `needs_information`
- `expert_review`

The LLM and agent swarm may extract evidence, maintain catalogs, generate
candidate configurations, critique designs, and explain results. They may not
override hard constraints or turn unsupported claims into facts.

### 4.5 Executable Decision Packet

The core output is not a narrative blueprint. It is a versioned decision packet:

- Approved requirement baseline.
- Two or three feasible alternatives.
- Explicit disqualifiers and rejected alternatives.
- Trade-off and sensitivity matrix.
- Signed architecture decision record.
- Provider-neutral architecture and selected implementation mapping.
- Requirement-to-control traceability.
- Executable Cedar/OPA policy, IaC assertions, and CI checks where possible.
- Isolation, failure, load, recovery, and cost validation plan.
- Dated bill of materials and cost range with assumptions.
- Implementation backlog with dependencies and exit criteria.
- Review conditions, expiry date, and reassessment triggers.

Chat becomes a secondary interface for explanation and navigation. The primary
workspace should be:

`Evidence | Alternatives | Decision | Controls | Reviews | Drift`

## 5. Architecture Outcome Network

The moat is the structured longitudinal dataset, not prompts, graph size, or chat
history.

### 5.1 Proprietary Objects

| Object | Purpose |
|---|---|
| `ContextSnapshot` | Immutable enterprise and workload context at decision time |
| `RecommendationRun` | Versions, feasible candidates, eliminated candidates, rules, predicted outcomes |
| `DecisionRecord` | Adopted, modified, rejected, or deferred decision; alternatives and rationale |
| `ImplementationInstance` | Actual deployed topology, offerings, versions, deviations, effort, and dates |
| `ControlVerification` | Test, result, evidence, effectiveness, exceptions, and expiry |
| `OutcomeObservation` | Baseline, target, observed value, denominator, horizon, and evidence quality |
| `FailureEvent` | Trigger, root cause, impact, missing control, remediation, and recurrence |
| `LearningGrant` | Consent, allowed fields, purposes, retention, revocation, and deletion lineage |

### 5.2 Outcome Labels

Capture normalized metrics rather than satisfaction:

- Time to first production workload.
- Architecture and roadmap variance.
- Engineering effort and operational toil.
- Builder onboarding lead time.
- Deployment frequency and change failure rate.
- Successful task rate, latency, availability, RTO, and RPO.
- Policy violations, audit findings, and approval latency.
- Cost per successful task, tenant, agent, and workflow.
- Forecast error and idle capacity.
- Incidents per million executions.
- Reusable capability adoption and abandoned workloads.

Every observation requires a time window, denominator, source, and evidence grade.
Collect at decision time and at 30, 90, and 180 days.

Do not learn from recommendation acceptance alone. Acceptance reflects politics,
skills, contracts, and budget. Rule changes require expert adjudication plus
implementation outcomes.

### 5.3 Privacy Boundary

Use three separate data planes:

1. **Tenant vault:** raw artifacts, exact costs, diagrams, policies, traces, and
   decisions; tenant-scoped authorization and encryption.
2. **Learning projection:** consented, structured, de-identified fields only; no
   raw cross-tenant text or embeddings.
3. **Benchmark service:** cohort aggregates only, with minimum cohort thresholds,
   rare-combination suppression, and export privacy controls.

Cross-tenant learning is optional. The product must still provide tenant-local
value through decision history, drift detection, actual-versus-estimated
reconciliation, and internal benchmarks.

## 6. How It Beats Claude And ChatGPT

The claim must be demonstrated, not asserted.

### 6.1 Benchmark

Build a 240-case benchmark:

- 80 anonymized retrospective engagements.
- 80 expert-authored boundary and trade-off cases.
- 40 incomplete or contradictory cases where abstention is correct.
- 40 temporal, provider-substitution, and counterfactual cases.
- Keep 25 percent permanently hidden.

Each case includes initial evidence, discoverable evidence, hidden hard
constraints, acceptable architecture sets, forbidden choices, catastrophic
failure conditions, dated provider facts, Pareto trade-offs, and expert rationale.

Compare:

- Platform Advisor.
- Current Claude baseline.
- Current ChatGPT baseline.
- Rules-only ablation.
- Human architect baseline.

Refresh frontier-model challengers quarterly.

### 6.2 Scoring

| Dimension | Weight |
|---|---:|
| Hard-constraint and safety correctness | 25 |
| Architecture and operating-model quality | 20 |
| Risk and control completeness/effectiveness | 15 |
| Feasibility, capacity, and economics | 10 |
| Alternatives and counterfactual reasoning | 10 |
| Evidence provenance and traceability | 8 |
| Calibration and appropriate abstention | 7 |
| Actionability | 5 |

A fabricated provider fact, missed critical constraint, or unsafe failure to
abstain is an automatic case failure.

### 6.3 Promotion Gates

- At least 65 percent blind pairwise wins against each frontier model.
- The 95 percent confidence-interval lower bound remains above 50 percent.
- At least a 10-point mean rubric improvement.
- Zero critical constraint violations.
- At least 95 percent recall for safety-critical abstention.
- At least 98 percent pass rate on invariant and monotonic counterfactual tests.
- Cost mean absolute percentage error below 25 percent after 90-day actuals exist.
- At least 50 percent reduction in architecture-review effort without lower quality.

Candidate rule changes progress through frozen replay, hidden benchmark, expert
review, production shadow mode, and a stratified canary.

## 7. Architect Workflow

1. **Create case:** define the architecture decision and primary workload.
2. **Build evidence room:** upload artifacts and validate extracted claims.
3. **Approve decision frame:** agree on constraints, priorities, and unknowns.
4. **Generate alternatives:** evaluate AWS-managed, OSS, and hybrid bundles.
5. **Run assurance:** inspect disqualifiers, controls, risks, economics, and
   counterfactuals.
6. **Decide:** select an option or record a governed override.
7. **Compile:** generate the ADR, controls, tests, estimate, and backlog.
8. **Review:** security, platform, operations, finance, and risk approve conditions.
9. **Observe:** ingest deployed state, actual cost, tests, incidents, and outcomes.
10. **Reassess:** reopen affected decisions when evidence, products, prices,
    regulations, or deployed state drift.

Architects return because the system owns decision history, evidence, approvals,
validation, and drift. A generated PDF alone creates no switching cost.

## 8. Repository Migration

### Preserve

- `AssessmentInput` and workload-specific profiles.
- The pure `DecisionEngine` boundary.
- Evidence gates and contradiction handling.
- Stable rule traces, overrides, and versioning.
- The local and AgentCore runtimes sharing one canonical package.

### Change First

1. Add tenant-scoped authorization before ingesting sensitive moat data.
2. Split `ComponentDecision` into provider-neutral capability and implementation
   decisions.
3. Move AWS mappings into the first provider adapter.
4. Replace single-answer output with alternatives, disqualifiers, and Pareto
   trade-offs.
5. Replace risk reduction by control presence with verified control effectiveness.
6. Separate evidence coverage from recommendation confidence everywhere.
7. Store source-backed claims, ADRs, implementations, tests, and outcomes.
8. Restore v2 counterfactual evaluation through cloned immutable assessments.

### Deprecate

- The legacy graph as a production decision authority.
- Acceptance-driven automatic rule-weight updates.
- The ten-panel sequence as the primary product model.
- AWS-only mappings inside the core architecture object.
- Fixed planning costs presented without uncertainty and reconciliation.
- Narrative blueprint generation as the definition of completion.

## 9. First 90 Days

### Weeks 1-3: Trust And Data Foundation

- Enforce tenant authorization and tenant-scoped artifact storage.
- Implement `EvidenceSource`, `EvidenceClaim`, `DecisionRecord`, and
  `LearningGrant`.
- Add immutable versioning and audit history.
- Define the regulated multi-tenant hosting benchmark rubric.

### Weeks 4-7: Alternatives Engine

- Introduce capability and implementation models.
- Convert AWS into a provider adapter.
- Add a Kubernetes/OSS adapter.
- Generate AWS-managed, OSS, and hybrid candidate bundles.
- Add hard-constraint elimination and rejected-option reasons.

### Weeks 8-10: Decision Assurance Packet

- Build the Evidence, Alternatives, Decision, and Controls workspace.
- Generate ADRs, executable control checks, validation plans, and backlogs.
- Add sensitivity analysis and immutable what-if cases.
- Run the system in shadow mode with principal architects.

### Weeks 11-13: Proof And Learning Loop

- Run blind evaluations against Claude and ChatGPT.
- Sign 5-10 design partners with required 30/90/180-day follow-ups.
- Capture expert adjudication, selected designs, deviations, actual effort, and
  initial control results.
- Publish benchmark results internally and enforce promotion gates.

## 10. Kill Criteria

Reposition or stop the product if the first 90-day validation shows:

- Independent principal architects do not prefer its decision packet in at least
  70 percent of blind reviews.
- A critical unsafe conclusion passes without expert escalation.
- Frontier models supplied the same artifacts perform within 10 percentage points.
- Architecture-review effort is not reduced by at least 50 percent.
- Fewer than five design partners pay without bundled consulting.
- Fewer than 60 percent run the generated validators or act on findings.
- Fewer than half permit de-identified outcome collection.
- Users value only the report and not evidence, assurance, controls, or drift.

## 11. North-Star Measure

The north-star metric is not sessions, questions answered, or accepted
recommendations.

It is:

> **Percentage of architecture decisions that remain constraint-compliant and
> meet their stated operational and economic outcomes at 90 and 180 days.**

