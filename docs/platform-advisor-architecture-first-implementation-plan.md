# Platform Advisor Architecture-First Implementation Plan

**Status:** Proposed execution plan
**Date:** 2026-07-30
**Governing vision:** `docs/platform-advisor-product-vision.md`
**Initial domain:** Enterprise agentic coding platforms
**Primary moat:** Governed architecture intelligence and implementation outcomes

## 1. Executive Decision

Do not rebuild the current questionnaire with a better chat interface.

Build three connected products in this order:

1. **Architecture intelligence:** versioned patterns, requirements, capabilities,
   offerings, compatibility, controls, evidence, economics, and benchmarks.
2. **Deterministic architecture workspace engine:** starts from a logical
   architecture, applies requirement revisions, computes feasible alternatives,
   and emits a replayable decision packet.
3. **Architecture-first workspace:** a persistent canvas that shows each
   architecture revision while chat proposes focused requirement and decision
   changes.

The language model is an interaction and research assistant. It may extract a
candidate requirement, find sources, propose catalog changes, and explain a
decision. It may not declare a product fact valid, bypass a hard constraint, or
mutate the customer architecture directly.

The first production-quality proof is not the canvas. It is a headless engine
that produces a correct, evidence-backed coding-platform decision packet from a
small set of progressively supplied requirements.

## 2. What Is Reusable

### Preserve

- Existing authentication, customer, and session shell.
- The v2 pure-kernel, typed-contract, deterministic serialization, evidence
  gating, trace, and human-override principles.
- Existing v2 behavior and tests as a regression boundary.
- AgentCore and local streaming transports as integration foundations.
- Existing cost, risk, roadmap, blueprint, and drill-down panels as future
  workspace lenses.
- The React Flow interaction concepts in `architecture-first-demo/`.

### Replace Or Isolate

- Do not extend the ten-step pipeline as the v3 product model.
- Replace `panelData[step]` with a typed, revisioned workspace projection.
- Replace operating-model-as-architecture with independent topology,
  deployment, operating-model, orchestration, and routing decisions.
- Replace direct `Component -> aws_services` mappings with provider-neutral
  capabilities, components, interfaces, and versioned offerings.
- Treat `knowledge_base/graph.json` as unverified source material, not decision
  authority.
- Retire fixed SVG architecture as the primary workspace.
- Do not reuse the demo's hard-coded catalog or decision logic in production.
- Quarantine unsupported cost and engagement claims until evidence review.

V3 is added beside v2 under `advisor_core/v3/`. V1 and v2 stay readable and
operational during migration.

## 3. Target Customer Workflow

```text
Create workspace
  -> load provider-neutral coding-platform reference architecture
  -> show assumptions, unresolved decisions, and current alternatives
  -> chat proposes one structured requirement patch
  -> user accepts, edits, or rejects the patch
  -> deterministic engine commits a new workspace revision
  -> canvas highlights the architecture delta and affected decisions
  -> engine selects the next highest-impact unresolved decision
  -> repeat until decision-ready or explicitly conditional
  -> compile the customer decision package
```

The first screen is useful before the customer answers anything. It contains the
logical platform across these independent planes:

1. Experience and developer interaction.
2. Identity, governance, and policy.
3. Agent orchestration and lifecycle.
4. Model access and routing.
5. Tool, data, and enterprise integration.
6. Isolated execution and workspace runtime.
7. Delivery, registry, and software supply chain.
8. Observability, evaluation, economics, and outcomes.

Named services appear only in the deployable view after constraints make a
mapping eligible. AgentCore Gateway is represented as a tool/API gateway, not a
generic model gateway. Agent memory is conversation/runtime memory, not the
architecture knowledge system.

### Focused Question Policy

Every question must declare its architectural effect before it is shown:

```text
question_id
unresolved_decision_ids
candidate_answers
candidate_elimination_count
affected_nodes
affected_controls
affected_cost_models
hard_constraint_risk
information_gain
why_now
```

Rank questions by:

1. Resolving a possible hard-constraint violation.
2. Eliminating the largest number of materially different candidates.
3. Changing topology, trust boundary, isolation, or control requirements.
4. Changing provider or offering eligibility.
5. Reducing material cost or outcome uncertainty.

Do not ask for information that only improves prose. A user may always choose
`unknown`; the engine then preserves alternatives or returns a conditional
decision instead of forcing an answer.

## 4. Target System Architecture

```text
                         KNOWLEDGE AUTHORING
Official sources -> snapshots -> candidate claims -> review -> Git catalog PR
                                                            |
                                                   catalog compiler
                                                            |
                                            signed CatalogRelease bundle
                                                            |
                 +--------------------------+---------------+----------------+
                 |                          |                                |
          search projection          runtime graph                   benchmark suite

                            CUSTOMER DECISION RUNTIME
Chat or artifact -> candidate RequirementPatch -> approve/edit/reject
                                                    |
                                             RequirementLedger
                                                    |
                                   deterministic v3 decision engine
                                                    |
              +----------------+--------------------+----------------+
              |                |                    |                |
       ArchitectureGraph  Alternatives        DecisionMatrix   AssurancePlan
              |                |                    |                |
              +----------------+------- DecisionPacket -------------+
                                       |
                              versioned workspace events
                                       |
                        canvas, inspector, lenses, export

                         IMPLEMENTATION AND LEARNING
Decision -> deployed instance -> control tests -> cost/incidents/outcomes
                                                |
                         consented de-identified learning projection
                                                |
                              expert-reviewed rule/catalog change
```

### Runtime Authority

The deterministic engine reads only:

- An immutable context and requirement revision.
- A pinned `CatalogRelease`.
- A pinned `RuleSetRelease`.
- Approved evidence claims included in that catalog release.
- Explicit customer evidence and overrides.

It does not read arbitrary retrieved passages during a decision run. Search and
RAG support source discovery, reviewer work, citations, and explanations.

## 5. Canonical V3 Contract

### Knowledge Definitions

```text
RequirementDefinition
ArchitecturePattern
PatternOverlay
Capability
ComponentDefinition
InterfaceContract
Offering
OfferingVariant
Threat
SecurityControl
ValidationTest
BestPractice
CostCapacityModel
OutcomeMetricDefinition
FailureMode
```

### Evidence And Releases

```text
EvidenceSource
SourceSnapshot
EvidenceClaim
ClaimReview
ContradictionSet
FreshnessPolicy
DecisionRule
CompatibilityRule
CatalogRelease
RuleSetRelease
```

### Customer Workspace

```text
ArchitectureWorkspace
ContextSnapshot
RequirementRevision
RequirementConstraint
RequirementPatch
WorkspaceRevision
ArchitectureGraph
ArchitecturePatch
DecisionPoint
QuestionCandidate
ArchitectureCandidate
CandidateBundle
RuleEvaluation
RecommendationRun
DecisionRecord
DecisionOverride
ExceptionWaiver
DecisionPacket
```

### Implementation And Outcomes

```text
ImplementationInstance
ImplementationDeviation
TestExecution
ControlVerification
OutcomeObservation
FailureEvent
DriftEvent
LearningGrant
```

### Non-Negotiable Trace

```text
SourceSnapshot -> EvidenceClaim -> Catalog object
RequirementRevision -> RequirementConstraint -> RuleEvaluation
ArchitecturePattern + Overlay -> ArchitectureCandidate
Candidate -> Capability -> Component -> OfferingVariant
OfferingVariant -> InterfaceContract -> CompatibilityRule
Threat -> SecurityControl -> ValidationTest -> ControlVerification
RecommendationRun -> DecisionRecord -> ImplementationInstance
ImplementationInstance -> OutcomeObservation | FailureEvent | DriftEvent
```

Every decision packet pins all input, catalog, ruleset, engine, evidence, and
revision versions. Replaying the packet must reproduce byte-equivalent engine
results.

## 6. Knowledge Moat Implementation

### Source Of Truth And Projections

| Store | Authoritative responsibility |
|---|---|
| Git | Schemas, ontology, rules, catalog definitions, reviewed public claim manifests, visible scenarios, release manifests |
| S3 | Immutable source snapshots, normalized source artifacts, tenant files, generated packages, restricted benchmark oracles |
| DynamoDB | Customer workspaces, requirement and architecture revisions, decisions, approvals, overrides, implementation and outcome records |
| OpenSearch or Bedrock Knowledge Bases | Rebuildable lexical/vector projection of approved claims and source passages |
| Compiled in-memory graph | Runtime dependency, compatibility, impact, and trace traversal |
| Neptune, later | Multi-hop analytical queries only after scale demonstrates a need |

Neither a vector database nor a graph database is the system of record.

### Publication Pipeline

```text
source registry
 -> scheduled fetch
 -> immutable snapshot, hash, and retrieval metadata
 -> structural parsing
 -> candidate atomic claims
 -> entity resolution and previous-version diff
 -> schema, citation, and contradiction checks
 -> domain review
 -> Git pull request
 -> catalog compile and benchmark suite
 -> signed release bundle
 -> search and graph projection rebuild
 -> canary
 -> active-release promotion
```

Each evidence claim is atomic and scoped by provider, product, variant, version,
region, configuration, deployment model, and effective date where applicable.
It includes exact source location, content hash, retrieval time, reviewer,
approval state, and expiry.

Critical claims require independent approval:

- Service and regional availability.
- Isolation and tenancy properties.
- Security and compliance eligibility.
- Pricing, quota, and capacity limits.
- Interface and version compatibility.
- Data residency and processing behavior.

Conflicting claims form a `ContradictionSet`; they are not silently resolved by
retrieval rank. Expired critical claims prevent `decision_ready`.

### Initial Source Registry

Start with a deliberately narrow, official-source corpus:

- AWS service, AgentCore, Bedrock, IAM, networking, observability, pricing, and
  regional availability documentation.
- Anthropic Claude Code and API documentation.
- OpenAI Codex and API documentation.
- GitLab SaaS API, CI/CD, identity, security, and integration documentation.
- Official documentation for selected CNCF and open-source runtime, policy,
  telemetry, and registry projects.
- NIST, OWASP, SLSA, and relevant compliance control sources.

Blogs can propose patterns and candidate claims. Product capability, security,
availability, compatibility, and pricing facts require authoritative sources.

### Freshness Defaults

| Claim class | Review interval |
|---|---:|
| Pricing, quotas, availability | 7-30 days |
| Interfaces and product capabilities | 30-90 days |
| Security and compliance assertions | 30-90 days |
| Stable architecture guidance | 180-365 days |

Source removal marks a claim stale but never deletes its decision history.

### Catalog Promotion States

```text
candidate -> machine_validated -> domain_reviewed -> benchmark_validated
          -> canary -> active -> superseded | withdrawn
```

Production workspaces pin a release. They never float to the latest catalog.
Upgrades run an impact analysis and create a new workspace revision.

## 7. Decision Engine

Implement the engine as pure stages:

1. Initialize the provider-neutral reference architecture.
2. Normalize a proposed requirement patch.
3. Detect contradictions and missing critical evidence.
4. Derive hard constraints, SLOs, threats, and required controls.
5. Generate deployment families and independent overlays.
6. Compute transitive capability and component dependency closure.
7. Query provider adapters for eligible offering variants.
8. Generate complete, configuration-aware bundles.
9. Reject violations and preserve every stable rejection reason.
10. Calculate economics and operational burden as ranges.
11. Produce the Pareto frontier and sensitivity analysis.
12. Generate the next high-impact question.
13. Commit an immutable workspace revision and architecture diff.
14. Compile the final decision packet.

Return one of:

- `decision_ready`
- `conditional`
- `needs_information`
- `expert_review`

Report evidence completeness, freshness, hard-constraint satisfaction,
recommendation stability, comparable-case sample size, and expert-review need
separately. Do not collapse these into one confidence score.

### Deployment Families

1. Developer-hosted local or IDE runtime.
2. Vendor-managed ephemeral cloud task.
3. Managed control plane with customer-hosted execution.
4. Persistent remote developer workspace.
5. Self-hosted VM or container platform.
6. Self-hosted Kubernetes platform.

### Independent Overlays

- Multi-agent supervisor and workers.
- Sequential specialist handoff.
- Parallel candidates with independent reviewer.
- Static multi-model binding.
- Capability, residency, or economics-based model routing.
- Model-provider fallback.
- Private connectivity or air gap.
- Warm pools and snapshots.
- Multi-region resilience.
- Human approval and pull-request transaction boundary.

### Economics

Model more than tokens:

```text
task arrival and concurrency
 x agent turns and tool calls
 x model routing distribution
 x input, output, and cache behavior
 x retry and failure probability
 + runtime, storage, network, observability, and control overhead
 = total platform cost
```

Primary normalized measures:

- Cost per successful coding task.
- Cost per accepted pull request.
- Cost per developer or active agent.
- Cost of failed and retried work.
- Forecast range and sensitivity drivers.

Every price and capacity input is a dated evidence claim. Remove the legacy
assumption that token volume alone represents economic value.

### Outcome Observability

Define a cross-system event contract joining:

```text
advisor decision -> coding-agent task -> model/tool/runtime spans
 -> GitLab issue/commit/MR -> CI result -> review/merge -> production outcome
```

Initial measures:

- Task success and human-intervention rates.
- Issue-to-merge time and rework.
- Accepted change rate and rollback rate.
- Policy violations and approval latency.
- Reliability and incidents per million executions.
- Cost per accepted pull request and successful task.
- Forecast-to-actual cost and implementation effort.

Collect baseline, 30-day, 90-day, and 180-day observations. Recommendation
acceptance is not proof that a rule was correct.

## 8. Backend, Persistence, And Events

### Persistence Boundary

Introduce an explicit tenant boundary and standardize all writers on one
repository. The API currently uses `CUSTOMER#`, AgentCore uses `CUST#`, and
authenticated routes do not consistently enforce customer/session ownership.
These are release-blocking defects, not deferred hardening.

Use append-only workspace revisions and derive current projections:

```text
PK: TENANT#{tenant_id}#WORKSPACE#{workspace_id}
SK: HEAD

PK: TENANT#{tenant_id}#WORKSPACE#{workspace_id}
SK: REVISION#{zero_padded_revision}
SK: EVENT#{zero_padded_sequence}
SK: DECISION#{decision_id}#REV#{revision}
SK: RUN#{recommendation_run_id}
SK: ARTIFACT#{artifact_id}#REV#{revision}
SK: IMPLEMENTATION#{implementation_id}
SK: OUTCOME#{metric_id}#{observed_at}
```

Store large packets and artifacts in S3 and retain immutable hashes and pointers
in DynamoDB. Use optimistic concurrency with `base_revision`; reject stale
writes instead of merging architecture state implicitly. Persist the revision,
event, and outbox record transactionally before publishing. Final chat messages
and architecture changes are durable; token deltas may remain transient.

### Command API

```text
POST /workspaces
GET  /workspaces/{id}
GET  /workspaces/{id}/revisions/{revision}
POST /workspaces/{id}/requirement-patches
POST /workspaces/{id}/requirement-patches/{patch_id}/accept
POST /workspaces/{id}/decisions/{decision_id}
POST /workspaces/{id}/recompute
POST /workspaces/{id}/catalog-upgrades
GET  /workspaces/{id}/decision-packet
GET  /workspaces/{id}/events?after={sequence}
GET  /workspaces/{id}/artifacts
POST /workspaces/{id}/exports
```

Use authenticated POST requests for commands. Do not place bearer tokens or
customer inputs in query parameters. The stream carries results; it does not
become the command transport.

### Versioned Event Envelope

```json
{
  "schema_version": "3.0",
  "event_id": "evt_...",
  "event_type": "architecture.revision.committed",
  "workspace_id": "ws_...",
  "sequence": 42,
  "base_revision": 6,
  "revision": 7,
  "correlation_id": "cmd_...",
  "occurred_at": "2026-07-30T00:00:00Z",
  "data": {}
}
```

Initial events:

```text
workspace.snapshot
requirement.patch.proposed
requirement.patch.accepted
requirement.patch.rejected
decision.question.raised
recommendation.started
recommendation.completed
architecture.revision.committed
decision.matrix.updated
economics.updated
outcome.plan.updated
artifact.updated
decision.packet.ready
command.rejected
```

Clients reduce events into a workspace projection. Reconnect starts after the
last applied sequence. Duplicate event IDs are idempotent. A revision commit
contains or references a deterministic architecture patch.

The authenticated principal supplies the tenant and actor identity. Customer,
workspace, and session identifiers from a browser payload are never accepted as
authorization evidence. Scope IAM to the intended runtime and artifact paths;
remove wildcard runtime invocation after the API-mediated command path reaches
parity.

## 9. Frontend Target, After Engine Gates

```text
+----------------------+--------------------------------+--------------------+
| Advisor conversation | Persistent architecture canvas | Component inspector|
| Requirement patches  | Logical / deployable toggle    | Why / evidence     |
| Decision prompts     | Revision diff and alternatives | Controls / status  |
+----------------------+--------------------------------+--------------------+
| Services | Controls | Economics | Outcomes | Roadmap | Decision trace      |
+----------------------------------------------------------------------------+
```

The canvas is the persistent center, not one pipeline step. Existing report
panels become lenses over the same pinned decision packet.

Chat produces visible `RequirementPatch` cards. The user accepts, edits, or
rejects them. Only the engine commits an architecture revision. The changed
nodes, edges, alternatives, controls, costs, and roadmap items are highlighted.

The production canvas uses `@xyflow/react` and deterministic automatic layout.
Coordinates never become architecture truth. The logical graph, deployable
graph, and visual layout are separate models.

## 10. Repository Change Map

### Add: V3 Core

```text
PlatformAdvisorAgent/app/PlatformAdvisorAgent/advisor_core/v3/
  models/
  catalog/
  engine/
  adapters/
  catalogs/
  benchmarks/
```

Core modules:

```text
engine/initialize.py
engine/normalize.py
engine/feasibility.py
engine/closure.py
engine/eligibility.py
engine/compatibility.py
engine/bundles.py
engine/questions.py
engine/controls.py
engine/economics.py
engine/outcomes.py
engine/ranking.py
engine/sensitivity.py
engine/revisions.py
engine/packet.py
```

Add `pipeline_skills/v3_workspace_skill.py` only after the headless v3 release
gates pass.

### Add: Backend

```text
backend/api/routers/workspaces.py
backend/api/routers/workspace_events.py
backend/api/db/workspaces.py
backend/api/models/workspace.py
backend/api/services/workspace_commands.py
backend/tests/test_workspace_contract.py
backend/tests/test_workspace_concurrency.py
backend/tests/test_workspace_replay.py
```

### Add: Frontend

```text
frontend/lib/workspace-types.ts
frontend/lib/workspace-events.ts
frontend/lib/workspace-reducer.ts
frontend/store/workspace-store.ts
frontend/components/workspace/ArchitectureWorkspace.tsx
frontend/components/workspace/ArchitectureCanvas.tsx
frontend/components/workspace/ArchitectureNode.tsx
frontend/components/workspace/CanvasToolbar.tsx
frontend/components/workspace/AdvisorConversation.tsx
frontend/components/workspace/RequirementPatchCard.tsx
frontend/components/workspace/DecisionPrompt.tsx
frontend/components/workspace/ComponentInspector.tsx
frontend/components/workspace/WorkspaceLenses.tsx
```

### Retain During Migration

- `advisor_core/engine.py` and v2 contracts.
- Existing session and panel endpoints.
- `SessionPageClient.tsx`, `StepIndicator`, and `PanelRouter` for v1/v2 sessions.
- Existing demo as a disposable interaction reference.

Route sessions by `engine_version`. Do not attempt to reinterpret a completed v2
panel sequence as a v3 workspace history.

## 11. Execution Plan

### Phase 0: Baseline, Tenancy, And Boundaries - Week 1 In Parallel

- Approve the vision, v3 authority boundary, stable ID rules, and record owners.
- Record current v2 test results and catalog inventory.
- Freeze `graph.json` and label unsupported facts.
- Correct or quarantine invalid cost assumptions.
- Create ADRs for source of truth, release pinning, event ordering, and v2/v3
  coexistence.
- Add tenant/customer/session ownership checks and cross-tenant denial tests.
- Unify API and AgentCore persistence behind one tenant-scoped repository.
- Protect or remove deployed local-development stream routes.
- Replace query-parameter tokens and inputs with authenticated POST commands.
- Add conditional writes, idempotency keys, and an event outbox contract.

Exit: no ambiguity remains about which store and process can publish a fact,
rule, decision, or architecture revision, and no principal can access another
tenant's workspace by changing a path or payload identifier.

### Phase 1: Contracts And Knowledge Compiler - Weeks 1-2

- Create v3 typed records and JSON schemas.
- Implement catalog loading, referential integrity, duplicate and cycle checks.
- Implement release manifests, content hashes, deterministic serialization, and
  signed-bundle hooks.
- Define the eight-plane reference architecture.
- Seed a small reviewed catalog and fixture scenarios.
- Implement immutable source snapshots and claim-review records.

Exit: a catalog release compiles deterministically; dangling, cyclic, duplicate,
unreviewed, stale-critical, and unpinned data fails closed.

### Phase 2: Architecture Kernel - Weeks 3-4

- Initialize the logical architecture without intake.
- Normalize requirement patches and preserve `unknown`.
- Implement contradiction checks, six deployment families, ten overlays,
  feasibility, dependency closure, and architecture diffs.
- Implement high-impact next-question selection.
- Build positive, rejection, unknown, and one-variable-flip scenarios for each
  deployment family.

Exit: the CLI can replay progressive answers and show exactly why each revision
changed the logical architecture and feasible set.

### Phase 3: Deployable Bundles - Weeks 5-6

- Add offering variants, interface contracts, and AWS/OSS/SaaS/BYOP adapters.
- Implement evidence-backed eligibility and configuration-aware compatibility.
- Generate complete bundles, rejection explanations, provider substitution, and
  dated cost/capacity ranges.
- Seed GitLab SaaS, Bedrock, Anthropic, OpenAI, selected AWS runtime services,
  and selected open-source variants deeply enough to prove compatibility.

Exit: no selected bundle has a missing dependency, incompatible interface, or
unsupported critical product claim.

### Phase 4: Assurance And Decision Packet - Weeks 7-8

- Add threats, controls, validation tests, and verified risk treatment.
- Add Pareto comparison, decision matrices, sensitivity analysis, best
  practices, token economics, outcome plan, and dependency-derived roadmap.
- Compile the complete versioned decision packet.
- Complete independent benchmarks, properties, and mutations.

Exit: the engine meets R0.3 quality gates and beats generic-model baselines on
constraint safety, completeness, traceability, reproducibility, and abstention.

### Phase 5: Workspace Persistence And API - Weeks 9-10

- Implement append-only revisions, event sequence, optimistic concurrency, and
  replay.
- Add command APIs and authenticated streaming.
- Standardize the DynamoDB customer key namespace.
- Add catalog upgrade impact analysis.
- Add AgentCore v3 tools after local contracts pass.

Exit: local and AgentCore paths produce the same workspace revisions from the
same command sequence.

### Phase 6: Architecture-First Workspace - Weeks 11-13

- Build workspace shell against frozen fixture packets first.
- Add persistent logical/deployable canvas, inspector, revision diff, and
  alternatives.
- Add requirement-patch chat flow and decision prompts.
- Convert existing panels into services, controls, economics, outcomes,
  roadmap, and trace lenses.
- Add replay, export, responsive behavior, accessibility, and visual tests.

Exit: a user can start from the reference architecture, answer focused
questions, inspect every change, and export a complete customer package.

### Phase 7: Outcome Loop And Pilot - Weeks 14-16

- Add implementation, deviation, verification, drift, and outcome capture.
- Instrument coding-task-to-GitLab/CI outcome correlation.
- Establish 30/90/180-day reviews and learning consent.
- Run three design-partner cases and adjudicate every disagreement.
- Promote rule changes only through the normal reviewed catalog release process.

Exit: the system captures whether recommendations were implemented and what
happened, without automatically learning from acceptance.

## 12. Parallel Workstreams And Ownership

| Workstream | Owns | Must not own |
|---|---|---|
| Contracts and compiler | Schemas, IDs, integrity, release manifest | Scenario oracles |
| Decision engine | Feasibility, closure, bundles, ranking, revisions | Catalog facts |
| Architecture knowledge | Patterns, offerings, claims, controls, economics | Engine code |
| Research operations | Fetch, snapshots, extraction, review workflow | Production approval alone |
| Independent verification | Hidden oracles, properties, mutations, benchmark reports | Rules under test |
| Platform API | Persistence, commands, events, auth, replay | Decision semantics |
| Workspace UX | Canvas, chat patches, inspector, lenses | Architecture authority |
| Outcome learning | Implementation and normalized outcomes | Automatic rule promotion |

Contracts and stable IDs are the first dependency. Knowledge and engine work
then proceed in parallel. API work starts when revision/event contracts freeze.
Frontend production integration starts when the decision-packet contract and
R0.3 engine gates pass.

## 13. First Two-Week Build Slice

This is the immediate executable backlog.

### Days 1-2: Freeze Contracts

- Add v3 package and stable ID/version conventions.
- Define `ArchitectureWorkspace`, `RequirementRevision`,
  `ArchitectureGraph`, `WorkspaceRevision`, `QuestionCandidate`,
  `RuleEvaluation`, and `DecisionPacket`.
- Write four ADRs: authority boundaries, catalog release, workspace revision,
  and v2 coexistence.
- Add v2 non-regression command to CI.
- In the parallel platform track, add cross-tenant denial tests, define the
  canonical tenant-scoped key format, and prevent new `CUST#` writes.

### Days 3-5: Catalog Compiler

- Add JSON schema-backed directories for patterns, overlays, capabilities,
  components, requirements, rules, evidence, and scenarios.
- Implement deterministic load, reference checks, duplicate checks, dependency
  cycle checks, release hash, and manifest.
- Add failing fixtures for every integrity rule.

### Days 6-7: Reference Architecture

- Author the eight planes.
- Seed 25-30 provider-neutral capabilities and their dependency graph.
- Author six deployment patterns and the first five overlays.
- Add 15-20 high-impact requirement definitions for the known target:
  5,000 developers, 1,000+ agents, GitLab SaaS, approved registries, Entra,
  multi-model providers, region flexibility, and action-dependent approvals.

### Days 8-9: Progressive Engine

- Initialize the architecture from no customer answers.
- Apply a requirement patch to create a new immutable revision.
- Implement hard-rule evaluation, dependency closure, architecture diff, and
  next-question ranking.
- Return feasible, rejected, and unknown candidates with stable reasons.

### Day 10: Proof And Review

- Run three progressive scenarios:
  1. Managed SaaS-first coding agents.
  2. Customer-hosted secure execution.
  3. Hybrid multi-model platform with BYOP integrations.
- Verify one-variable flips and deterministic replay.
- Demo a CLI or JSON sequence:

```text
initial architecture
 -> proposed requirement patch
 -> accepted revision and highlighted diff
 -> next high-impact question
 -> alternatives and rejection reasons
 -> partial decision packet
```

### Two-Week Definition Of Done

- No production UX changes.
- No LLM in the decision path.
- V1/v2 behavior and tests unchanged.
- A release-pinned, provider-neutral logical architecture exists before intake.
- At least three requirement answers visibly and correctly alter architecture.
- Every change traces to a requirement, rule, and catalog release.
- Missing dependencies fail closed.
- The next question states what architecture decision it can change.
- The output replays byte-for-byte from the same inputs.

## 14. Release Quality Gates

### Initial Artifact Minimums

| Artifact | R0.3 minimum |
|---|---:|
| Architecture patterns | 6 |
| Overlays | 10 |
| Requirement definitions | 50 |
| Capabilities | 35 |
| Component definitions | 45 |
| Interface contracts | 15 |
| Offering variants | 30 |
| Hard feasibility rules | 60 |
| Dependency and compatibility rules | 60 |
| Threats | 30 |
| Security controls | 40 |
| Validation tests | 40 |
| Source snapshots | 60 |
| Evidence claims | 250 |
| Cost and capacity models | 15 |
| Architect-authored scenarios | 60 |
| Hidden scenario oracles | 15+ |
| BYOP manifests | 20 |
| Generated counterfactuals | 500+ |

### Safety And Correctness

- 100% hard-constraint safety.
- 100% expected abstention when critical evidence is missing.
- 100% referential integrity and deterministic replay.
- Zero selected missing dependencies or incompatible offerings.
- Zero unverified controls reducing residual risk.
- At least 95% agreement on feasible/rejected sets after adjudication.
- At least 95% required capability and control recall.
- At least 90% agreement on the acceptable Pareto set.
- At least 90% non-equivalent mutation kill rate and 100% for mutations that
  could admit hard-constraint violations.

### Generic Model Comparison

Compare the same held-out evidence packets with current frontier Claude and
ChatGPT models. Score hard violations, missing dependencies, unsupported facts,
alternative recall, provider substitution, reproducibility, trace completeness,
and appropriate abstention.

The v3 engine passes only with zero hard-constraint violations, at least 95%
safety-abstention recall, at least 65% blind pairwise wins against each model,
and a 95% confidence-interval lower bound above 50%. Prose preference is not a
moat metric.

### Architect Review

Use three independent principal architects. Require:

- 100% agreement on safety-critical outcomes.
- At least 90% agreement on feasibility and rejection after adjudication.
- Inter-rater kappa of at least 0.70.

Every disagreement becomes a scenario, catalog correction, rule change, or
explicit unsupported coverage boundary. It does not become a prompt-only fix.

## 15. Migration And Operational Risks

### V2 Coexistence

- Existing v2 sessions remain rendered by the current step/panel UI.
- New workspaces explicitly set `engine_version: 3`.
- V2 may be imported only as an unverified context snapshot, never fabricated
  into a v3 event history.
- V3 releases remain dark until the benchmark gates pass.

### Immediate Risks To Correct

1. Authenticated routes do not consistently enforce customer/session ownership.
2. AgentCore and API customer partition prefixes disagree.
3. Production runtime exposure and wildcard browser invoke permissions require a
   separate security hardening review.
4. Local SSE currently sends token and input in query parameters.
5. Mutable full-context writes can lose concurrent updates.
6. Current controls can lower risk without verification evidence.
7. Current dependency behavior can silently omit required components.
8. Legacy cost facts and calculations are not decision-grade.
9. The current source publication path lacks review and release promotion.
10. The frontend export call has no implemented backend artifact contract.
11. There are no frontend reducer, canvas, replay, or visual regression tests.

## 16. Success Measure

The product is succeeding when an architect can:

1. See a credible logical architecture immediately.
2. Provide a requirement conversationally without completing a long intake.
3. See exactly what changed and why.
4. Compare feasible AWS, open-source, SaaS, and BYOP bundles.
5. Challenge every fact, assumption, rule, control, and cost input.
6. Reproduce the same answer from pinned versions.
7. Export an implementable package, not generic architecture prose.
8. Return after implementation and measure whether the design delivered the
   intended security, delivery, reliability, and economic outcomes.

That closed decision-to-outcome loop is the durable moat.
