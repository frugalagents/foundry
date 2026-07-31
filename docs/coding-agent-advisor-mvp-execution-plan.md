# Coding-Agent Platform Advisor: Engine-First MVP Plan

**Status:** Execution plan
**Date:** 2026-07-28
**Scope:** Artifacts, deterministic core engine, and proof tests only
**Deferred:** Chat, frontend, persistence migration, production deployment, and autonomous crawling

## 1. What We Are Building

Build a headless architecture decision system for enterprise coding-agent
platforms. Given a versioned requirement profile, it must return:

1. Feasible and rejected deployment architectures.
2. Required multi-agent, multi-model, networking, lifecycle, and approval
   overlays.
3. Complete capability and component dependencies.
4. Compatible AWS, open-source, SaaS, and bring-your-own-platform bundles.
5. Required threats, controls, and verification tests.
6. Explicit trade-offs, assumptions, unknowns, and disqualifiers.
7. A replayable decision packet with a trace to rules and source evidence.

The engine flow is:

```text
Versioned requirements
  -> evidence and contradiction gates
  -> hard-constraint feasibility
  -> architecture candidates and overlays
  -> capability and component closure
  -> eligible offering variants
  -> interface and compatibility evaluation
  -> complete candidate bundles
  -> controls and verification requirements
  -> trade-off and sensitivity analysis
  -> versioned decision packet
```

The LLM is not part of this MVP's decision path. Later, an LLM may translate
conversation into proposed requirement patches and explain engine output. It
may not select an architecture, weaken a constraint, or invent a product fact.

## 2. Why This Can Beat A Generic Chat Answer

A generic model can produce plausible prose. This engine must produce artifacts
that a generic response does not reliably provide:

- Exhaustive elimination against explicit hard constraints.
- Complete dependency closure with no silently omitted components.
- Version- and configuration-aware compatibility across products.
- Provider substitution without changing provider-neutral requirements.
- Stable rule IDs and machine-checkable reasons for every decision.
- Source-backed product claims with freshness and review state.
- Controls that count only when a verification contract exists.
- Counterfactual and mutation-tested recommendation behavior.
- Exact replay from requirements, catalog, ruleset, and evidence versions.

The initial moat is the normalized ontology, rules, compatibility knowledge, and
benchmark corpus. The durable moat later becomes implementation and outcome
data connected to these same records.

## 3. Existing Code: Reuse And Boundary

Keep v1 and v2 read-only and behaviorally unchanged.

Reuse:

- The pure-kernel principle in
  `PlatformAdvisorAgent/app/PlatformAdvisorAgent/advisor_core/engine.py`.
- Pydantic contracts, deterministic serialization, evidence gating, traces,
  and recorded overrides.
- The current v2 tests as a regression boundary.
- Existing pipeline and API code only as future integration references.

Do not carry these v2 semantics into v3:

- Treating operating model as deployment architecture.
- Combining model gateway with tool gateway.
- Combining agent registry with tool registry.
- Mapping coarse components directly to AWS services.
- Dropping dependencies that are not already active.
- Reducing risk because a control name is present.
- Returning one AWS-oriented answer without rejected alternatives.
- Using fixed component prices as architecture truth.

Add `advisor_core/v3/` as an isolated package. No v3 code should be imported by
the production runtime until all engine release gates pass.

## 4. Architecture Scope

### Deployment Families

1. Developer-hosted local or IDE runtime.
2. Vendor-managed ephemeral cloud task.
3. Managed control plane with customer-hosted execution.
4. Persistent remote developer workspace.
5. Self-hosted VM or container platform.
6. Self-hosted Kubernetes platform.

### Independent Overlays

1. Multi-agent supervisor and workers.
2. Sequential specialist handoff.
3. Parallel candidates with independent reviewer.
4. Static multi-model binding.
5. Capability, cost, or residency-based model routing.
6. Model-provider fallback.
7. Private connectivity or air gap.
8. Warm pools and snapshots.
9. Multi-region resilience.
10. Human approval and pull-request transaction boundary.

Deployment, operating model, orchestration, model routing, and isolation are
separate decisions. One must not stand in for another.

## 5. Canonical V3 Records

### Catalog Definitions

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
CostCapacityModel
OutcomeMetricDefinition
FailureMode
```

### Rules And Evidence

```text
DecisionRule
CompatibilityRule
EvidenceSource
SourceSnapshot
EvidenceClaim
CatalogRelease
RuleSetRelease
```

### Case Inputs And Engine Results

```text
ContextSnapshot
RequirementField
RequirementConstraint
BYOPManifest
ArchitectureCandidate
CandidateBundle
RuleEvaluation
RecommendationRun
ArchitectureDecision
DecisionOverride
ExceptionWaiver
DecisionPacket
```

### Later Lifecycle Records

Define their contracts now, but do not use them for MVP ranking:

```text
ImplementationInstance
TestExecution
OutcomeObservation
FailureEvent
LearningGrant
```

### Benchmark Records

```text
BenchmarkScenario
ScenarioOracle
BenchmarkRun
```

## 6. Canonical Trace

```text
CatalogRelease PINS catalog objects, evidence claims, and RuleSetRelease

EvidenceSource -> SourceSnapshot -> EvidenceClaim
ContextSnapshot -> RequirementField
RequirementDefinition + RequirementField -> RequirementConstraint

DecisionRule EVALUATES RequirementConstraint
ArchitecturePattern + PatternOverlay -> ArchitectureCandidate
ArchitectureCandidate REQUIRES Capability
Capability REALIZED_BY ComponentDefinition
ComponentDefinition IMPLEMENTED_BY OfferingVariant
OfferingVariant PROVIDES/REQUIRES InterfaceContract
CompatibilityRule EVALUATES version, configuration, region, and topology

CandidateBundle IMPLEMENTS ArchitectureCandidate
RuleEvaluation records SATISFIES | VIOLATES | UNKNOWN
RecommendationRun contains feasible and rejected CandidateBundles
ArchitectureDecision SELECTS one result from RecommendationRun

SecurityControl MITIGATES Threat
ValidationTest VERIFIES SecurityControl
DecisionPacket freezes the full decision and evidence trace
```

Compatibility must not be a static pairwise `offering A works with offering B`
claim. It depends on offering variant, interfaces, configuration, region, and
topology.

## 7. Minimum Artifact Inventory

These are release gates:

| Artifact | Minimum |
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
| Architect-authored scenarios | 60, ten per architecture family |
| Hidden scenario oracles | 15 or more |
| BYOP manifests | 20 |
| Generated counterfactuals | 500 or more |

Initial offerings must cover enough AWS, open-source, SaaS, and BYOP variants to
prove substitution. Candidate products include AgentCore, Lambda MicroVMs,
CodeBuild, ECS/Fargate, EKS, OpenHands, Coder, Kubernetes Jobs, Firecracker,
gVisor, Kata Containers, OPA, Anthropic, OpenAI, GitHub, and customer-defined
endpoints. Inclusion is a research hypothesis until supported by reviewed
evidence claims.

## 8. Three Incremental Engine Releases

### R0.1: Architecture Kernel

Build:

- V3 contracts and immutable JSON catalog format.
- Six deployment patterns and ten overlays.
- Requirement normalization and contradiction handling.
- Hard feasibility rules.
- Architecture candidate generation.
- Capability and component transitive dependency closure.
- Feasible, rejected, and unknown results with stable rule traces.

Do not select named products in this release.

Exit gates:

- All six patterns are reachable.
- Every pattern has positive, rejection, incomplete-evidence, and
  one-variable-flip scenarios.
- A missing dependency makes the candidate incomplete or rejected; it is never
  silently removed.
- Identical versioned inputs produce byte-equivalent results.
- V1 and v2 regression tests remain unchanged and pass.

### R0.2: Implementable Bundles

Build:

- Offerings and versioned offering variants.
- Interface contracts for identity, model APIs, tools, telemetry, policy,
  source control, secrets, artifacts, and execution.
- Eligibility and compatibility evaluation.
- Complete bundle generation.
- AWS, OSS, SaaS, and BYOP provider adapters.
- Evidence claims, snapshots, freshness policies, quotas, licensing,
  operational burden, and cost/capacity models.
- Provider-substitution and portability analysis.

Exit gates:

- No selected bundle contains a missing or incompatible dependency.
- Every critical product assertion has approved, non-expired evidence.
- At least ten benchmark scenarios have both AWS and non-AWS feasible bundles.
- Replacing a provider changes offerings and trade-offs, not neutral
  requirements.
- Unsupported BYOP claims remain `unknown` and cannot satisfy a hard constraint.

### R0.3: Decision Assurance

Build:

- Threat and control mapping.
- Control verification contracts.
- BYOP gap and remediation analysis.
- Pareto trade-off and sensitivity analysis.
- Decision states: `decision_ready`, `conditional`, `needs_information`, and
  `expert_review`.
- Replayable decision packet.
- Full benchmark and catalog quality reports.

Do not use outcome-based ranking yet. First collect actual implementation and
outcome records.

Exit gates:

- A control affects residual risk only when required verification is defined and
  acceptable evidence is present.
- Stale critical evidence blocks `decision_ready`.
- Every result traces from requirement through rule, architecture, capability,
  component, offering, control, and evidence.
- The packet records requirement revision, catalog release, ruleset release,
  engine version, all alternatives, all evaluations, and all assumptions.
- Sensitivity analysis identifies which input changes can alter the decision.

## 9. Six-Week Execution

### Week 1: Contracts And Catalog Compiler

- Create the isolated `advisor_core/v3/` package.
- Define typed records and stable ID conventions.
- Define JSON schemas and per-record directories.
- Implement catalog loading, referential integrity, cycle detection, duplicate
  detection, release hashing, and deterministic serialization.
- Add v1/v2 non-regression checks.

Gate: an empty but structurally valid catalog release compiles; malformed,
cyclic, dangling, duplicate, or unpinned records fail closed.

### Week 2: Architecture Kernel And R0.1 Data

- Author six patterns, ten overlays, requirements, capabilities, components,
  and initial hard rules.
- Implement contradiction checks, feasibility, candidate generation, and
  dependency closure.
- Author at least 24 seed scenarios covering every pattern and failure state.

Gate: R0.1 exit criteria pass.

### Week 3: Offerings, Interfaces, And Evidence

- Author offering and offering-variant records.
- Define interface contracts and provider adapters.
- Add immutable source snapshots, evidence claims, freshness, and review state.
- Implement offering eligibility.

Gate: no product fact can enter a decision without a claim and source snapshot.

### Week 4: Compatibility, Bundles, And R0.2

- Implement configuration-aware compatibility rules.
- Generate complete bundles and explain all bundle rejection reasons.
- Add cost/capacity and operational-burden models.
- Add provider-substitution, version-boundary, and BYOP tests.

Gate: R0.2 exit criteria pass.

### Week 5: Security, Verification, And Decision Packets

- Author threats, controls, and validation-test definitions.
- Implement verified-control risk treatment.
- Add BYOP gap analysis, Pareto comparison, sensitivity analysis, and packet
  generation.

Gate: every risk treatment and selected bundle is traceable and replayable.

### Week 6: Independent Benchmark And R0.3

- Complete 60 architect-authored scenarios, including at least 15 whose oracles
  remain hidden from engine and catalog authors.
- Generate at least 500 one-variable and boundary counterfactuals.
- Generate at least 10,000 valid and invalid requirement sets for property
  testing.
- Run property, mutation, stale-evidence, dependency, provider-substitution,
  BYOP, determinism, and replay tests.
- Conduct blind review with three experienced principal architects.
- Convert every disagreement into a scenario, rule, catalog, or documented
  coverage boundary; never a prompt-only fix.

Gate: R0.3 exit criteria and all benchmark thresholds pass.

## 10. Parallel Workstreams

### A. Schema And Catalog

Owns record contracts, JSON schemas, catalog layout, compiler, release manifest,
and integrity validation.

### B. Decision Engine

Owns requirement normalization, hard constraints, candidate generation,
dependency closure, compatibility, bundle generation, ranking, sensitivity, and
decision packets.

### C. Architecture Knowledge

Owns patterns, overlays, capabilities, components, offerings, rules, threats,
controls, evidence claims, and source review.

### D. Verification

Owns independent scenario oracles, counterfactual generation, properties,
mutations, benchmark reports, and architect adjudication.

Schema contracts and stable IDs are agreed first. Knowledge authors must not
change engine code to force an expected answer, and engine authors must not
write the independent scenario oracles they are evaluated against.

## 11. Test Strategy And Pass Thresholds

### Catalog Integrity

- 100% referential integrity.
- Zero dependency cycles unless a relationship type explicitly permits them.
- 100% of critical offering claims have approved, current evidence.
- Release content hash and object versions reproduce exactly.

### Golden Scenarios

- 60 independent scenarios, ten per architecture family and at least 25% hidden
  from engine and catalog authors.
- 100% hard-constraint safety: no forbidden architecture or bundle is selected.
- At least 95% agreement on feasible/rejected sets after adjudication.
- At least 95% of required capabilities and controls are present.
- At least 90% agreement on the acceptable Pareto set.
- 100% expected abstention when critical information is missing.

### Counterfactuals And Properties

- 500 or more generated cases.
- 10,000 or more generated valid and invalid requirement sets per release.
- One-variable changes produce only declared downstream changes.
- Tightening a hard constraint never introduces a newly feasible candidate.
- Adding an optional preference never revives a hard-rejected candidate.
- Provider substitution preserves neutral requirements and capabilities.
- Input and catalog ordering never change the result.
- No infeasible bundle, missing dependency, incompatible offering, or unverified
  risk reduction is ever selected.

### Mutation Tests

Seed faults in:

- hard-rule predicates;
- dependency edges;
- compatibility rules;
- evidence expiry;
- control verification;
- ranking weights.

The benchmark must kill at least 90% of non-equivalent mutations and 100% of
mutations that could admit a hard-constraint violation.

### BYOP

- At least 20 manifests covering complete, partial, forged, stale, and
  incompatible customer platforms.
- Unsupported or self-attested claims never satisfy a verified hard constraint.
- Every missing capability produces a traceable remediation item.
- All incompatible interfaces and offering variants are reported explicitly.

### Generic-LLM Comparison

Use a fixed prompt and the same held-out evidence packets with current Claude
and ChatGPT models. Score both systems on:

- hard-constraint violations;
- missing dependencies;
- unsupported product claims;
- feasible alternatives recalled;
- reproducibility;
- trace completeness;
- provider substitution;
- appropriate abstention.

The engine passes only if it has zero hard-constraint violations, at least 95%
safety-abstention recall, at least 65% blind pairwise wins against each model,
and a 95% confidence-interval lower bound above 50%. It must also outperform the
generic responses on dependency completeness, traceability, reproducibility,
and unsupported claims. Prose quality is not a moat metric.

## 12. Proposed Package Layout

```text
PlatformAdvisorAgent/app/PlatformAdvisorAgent/advisor_core/v3/
  __init__.py
  models/
    catalog.py
    requirements.py
    evidence.py
    decisions.py
    benchmarks.py
  catalog/
    loader.py
    compiler.py
    validators.py
  engine/
    normalize.py
    feasibility.py
    closure.py
    eligibility.py
    compatibility.py
    bundles.py
    controls.py
    ranking.py
    sensitivity.py
    packet.py
  adapters/
    base.py
    aws.py
    oss.py
    saas.py
    byop.py
  catalogs/
    releases/
    requirements/
    architectures/
    overlays/
    capabilities/
    components/
    interfaces/
    offerings/
    rules/
    threats/
    controls/
    tests/
    evidence/
  benchmarks/
    scenarios/
    oracles/
    generated/
```

Keep the modules pure: no network, database, UI, or model calls. Source
collection is a separate future process that proposes reviewed catalog changes.

## 13. Definition Of Done

The engine-first MVP is complete only when:

1. R0.1, R0.2, and R0.3 are immutable and replayable.
2. All artifact minimums are met.
3. Every hard rejection has a stable rule ID and evidence.
4. Every selected component and offering has complete dependencies.
5. Multi-agent and multi-model needs alter overlays and components correctly.
6. AWS can be substituted with eligible OSS, SaaS, or BYOP offerings where the
   requirements permit it.
7. Critical unknowns and stale claims force abstention.
8. Controls do not reduce risk without verification.
9. The independent benchmark and mutation thresholds pass.
10. Three architects reach at least 90% agreement on feasibility and rejection,
    100% agreement on safety-critical cases, and inter-rater kappa of at least
    0.70.
11. Existing v2 tests still pass without changing v2 behavior.

Only after this definition of done should work begin on conversational intake,
the frontend, transactional persistence, production deployment, or automated
catalog maintenance.
