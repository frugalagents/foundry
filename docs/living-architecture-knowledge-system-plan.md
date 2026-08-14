# Living Architecture Knowledge System Plan

**Status:** Proposed execution baseline
**Date:** 2026-08-11
**Governing vision:** `docs/platform-advisor-product-vision.md`
**Related plan:** `docs/platform-advisor-architecture-first-implementation-plan.md`
**Initial domain:** Enterprise coding-agent platforms
**Primary objective:** Maintain current, evidence-backed knowledge of platform
capabilities, implementations, compatibility, decision boundaries, and outcomes.

## 1. Executive Decision

Freeze the provider-neutral logical architecture at a useful level of
completeness. Stop expanding the deterministic rule engine until the product can
continuously detect, review, publish, and assess changes in the technologies that
implement that architecture.

Build the following system:

```text
authoritative sources
  -> immutable snapshots and structural diffs
  -> agent-proposed atomic claims and relationships
  -> architect-reviewed OKF-compatible knowledge changes
  -> schema validation, scenarios, and release compilation
  -> immutable signed CatalogRelease
  -> graph/search projections and the Platform Advisor runtime
  -> customer decisions, implementations, and measured outcomes
  -> reviewed knowledge improvements
```

The architecture knowledge is the product. The engine is a consumer of a pinned
knowledge release.

## 2. Scope And Non-Goals

### In Scope

- A small provider-neutral ontology for coding-agent platforms.
- A governed registry of authoritative information sources.
- Versioned source snapshots and change detection.
- Agent-assisted claim and relationship extraction.
- Human review of decision-critical knowledge.
- OKF-compatible Markdown and YAML authoring.
- Compilation into the existing v3 `CatalogRelease` contract.
- Search, vector, and typed-relationship projections.
- Catalog drift and customer-impact analysis.
- Decision, implementation, control, cost, incident, and outcome feedback.

### Not In Scope For The First 90 Days

- Adding more platform domains beyond coding-agent platforms.
- Building a general-purpose enterprise ontology.
- Introducing a graph database before compiled relationship traversal is
  demonstrably insufficient.
- Allowing an LLM or ingestion agent to publish decision-grade facts directly.
- Replacing the existing deterministic hard-constraint engine.
- Encoding subjective preferences as large collections of hard rules.
- Generating production infrastructure from unverified product claims.

## 3. Authority Boundaries

| Concern | Authority |
|---|---|
| Capability identity and meaning | Reviewed semantic model |
| Product capability or limitation | Approved evidence claim |
| Dependency and incompatibility | Typed relationship backed by evidence |
| Hard feasibility constraint | Deterministic engine |
| Soft trade-off and explanation | Decision pattern plus cited evidence |
| Knowledge discovery | Lexical/vector retrieval |
| Catalog publication | Reviewed and tested release pipeline |
| Customer architecture | Pinned catalog release plus accepted requirements |
| Product improvement | Reviewed customer decision and outcome observations |

Research agents may collect, compare, extract, summarize, cross-link, and propose.
Architects approve semantic identity, equivalence, critical claims, conflicts,
`recommended_when`, `avoid_when`, and outcome interpretations.

## 4. Minimal Semantic Model

Start with eight entities:

| Entity | Purpose |
|---|---|
| `Capability` | Provider-neutral ability the platform needs |
| `Component` | Logical architectural responsibility providing capabilities |
| `Offering` | Named provider, SaaS, or open-source implementation |
| `Variant` | Version, edition, region, deployment, or configuration of an offering |
| `Interface` | Protocol or contract through which components interact |
| `Claim` | Atomic, scoped, source-backed statement |
| `DecisionPattern` | Evidence-backed guidance for when to use or avoid an option |
| `OutcomeObservation` | Measured result from an implemented decision |

Use a small set of typed relationships:

```text
IMPLEMENTS
REQUIRES
COMPATIBLE_WITH
INCOMPATIBLE_WITH
ALTERNATIVE_TO
INTEGRATES_WITH
RECOMMENDED_WHEN
AVOID_WHEN
SUPPORTED_BY
SUPERSEDES
```

Every relationship must include provenance, effective dates, review status, and
freshness. Do not infer equivalence from similar names.

## 5. Capability Knowledge Page

Each stable logical capability has one reviewed knowledge page:

```yaml
kind: Capability
id: capability:isolated-execution
title: Isolated agent execution
status: active
summary: Execute agent-generated or untrusted code with workload isolation.

requires:
  - capability:workload-identity
  - capability:network-policy

implementations:
  - offering:serverless-microvm
  - offering:managed-container
  - offering:kubernetes-sandbox

recommended_when:
  - untrusted code execution
  - multi-tenant workloads
  - strong tenant isolation

avoid_when:
  - no code execution is permitted
  - the workload is a trusted local-only developer task

claims:
  - claim:isolated-execution-workload-boundary
```

Offering and claim pages contain provider, product, variant, version, region,
pricing or quota scope, source snapshot, effective date, reviewer, and
`stale_after`.

## 6. Source Portfolio

### Tier A: Decision Authority

Facts from these sources may support hard compatibility and eligibility after
review.

| Source class | Examples | Claims collected | Default check |
|---|---|---|---|
| Official product documentation | Provider developer and administration docs | Features, limits, interfaces, controls, configuration | Weekly |
| Official release notes and changelogs | Cloud, model, coding-agent, IDE, and SCM releases | Additions, removals, breaking changes, deprecations | Daily |
| Official API and schema references | REST, SDK, OpenAPI, event schemas | Operations, fields, auth, limits, error contracts | Weekly |
| Official pricing and quota pages | Model, runtime, storage, search, network | Unit prices, tiers, quotas, capacity assumptions | Daily |
| Official regional availability | Cloud region and service availability pages | Region, partition, residency, feature availability | Daily |
| Official security and compliance docs | Encryption, identity, audit, certifications | Control implementation and verification requirements | Weekly |
| Protocol specifications | MCP, A2A, OpenAPI, OAuth/OIDC, OCI | Protocol versions, transports, discovery, auth, compatibility | On release |
| Software supply-chain standards | SLSA, SPDX, CycloneDX, Sigstore | Provenance, SBOM, signing, attestations | On release |

### Tier B: Operational Guidance

These sources support patterns and implementation guidance but do not override
Tier A product facts.

| Source class | Examples |
|---|---|
| Official reference architectures | Cloud architecture centers and Well-Architected guidance |
| Official samples and repositories | Provider-owned Git repositories, examples, SDKs, and templates |
| Maintainer release repositories | Tagged releases, migration guides, ADRs, and issue trackers |
| Observability specifications | OpenTelemetry GenAI and agent semantic conventions |
| Security frameworks | NIST AI RMF, OWASP Agentic Security, MITRE ATLAS |
| Security advisories | Vendor advisories, CVEs, GitHub Security Advisories |

### Tier C: Comparative Evidence

Tier C may create candidate claims and decision patterns. It cannot establish
critical product facts without corroboration.

- Reproducible benchmarks such as coding-task and agent-tool evaluations.
- Peer-reviewed papers and artifact-backed technical reports.
- Independent implementation studies with disclosed methods.
- Conference talks and engineering blogs from identifiable practitioners.

### Tier D: Proprietary Outcome Evidence

This is the compounding moat:

- Customer context and constraints.
- Options considered and rejected.
- Recommendation and rationale.
- Customer override and reason.
- Implemented configuration and deviations.
- Control-test and assurance results.
- Cost, latency, reliability, and operational incidents.
- Delivery, quality, adoption, and business outcomes.
- Failure modes and remediation.

## 7. Initial Source Coverage

Create source groups for:

1. Coding-agent products and IDE integrations.
2. Source-control and CI/CD platforms.
3. Agent runtime, memory, gateway, and identity platforms.
4. Foundation-model providers, model catalogs, pricing, and quotas.
5. MCP, A2A, OpenAPI, OAuth/OIDC, OCI, and related specifications.
6. Sandboxes, containers, microVMs, Kubernetes, and serverless runtimes.
7. Artifact, package, tool, prompt, skill, and agent registries.
8. Policy engines, secrets, identity brokers, and authorization systems.
9. OpenTelemetry, evaluation frameworks, and coding-agent benchmarks.
10. NIST, OWASP, MITRE, SLSA, SPDX, CycloneDX, Sigstore, CVE, and vendor
    advisories.

Prioritize depth over breadth. The initial release should cover three
representative implementation ecosystems end to end before adding more vendors.

## 8. Target Architecture

```text
                              SOURCE PLANE
 SourceRegistry -> scheduler -> collector -> raw snapshot -> structural diff
                                      |
                                      v
                           KNOWLEDGE ENRICHMENT
                 ClaimCandidate + RelationshipCandidate
                                      |
                            contradiction detection
                                      |
                                      v
                             REVIEW AND AUTHORING
                     Git PR with OKF Markdown/YAML
                                      |
                     architect approval or rejection
                                      |
                                      v
                              RELEASE COMPILER
 schemas -> IDs -> references -> evidence -> freshness -> scenarios -> signing
                                      |
                         immutable CatalogRelease bundle
                                      |
                  +-------------------+-------------------+
                  |                   |                   |
            graph projection    lexical/vector index   benchmark report
                  |                   |                   |
                  +-------------------+-------------------+
                                      |
                             DECISION RUNTIME
 RequirementPatch -> hard constraints -> alternatives -> decision trace
                                      |
                            pinned workspace revision
                                      |
                                      v
                         IMPACT AND LEARNING PLANE
 release diff -> affected decisions -> reassessment -> implementation outcomes
                                      |
                           reviewed knowledge change
```

### MVP AWS Mapping

| Capability | Initial implementation |
|---|---|
| Source registry and jobs | DynamoDB |
| Scheduling | EventBridge Scheduler |
| API/RSS/Git collectors | Lambda |
| Complex document collection | Container task only when Lambda is insufficient |
| Immutable snapshots | Versioned S3 objects with content hashes |
| Claim extraction | Bedrock structured output |
| Human review | Git pull requests |
| Authored knowledge | Git Markdown/YAML using OKF-compatible metadata |
| Validation and compilation | Existing Python compiler in CI |
| Release storage | Versioned S3 bundle with KMS signature |
| Search and retrieval | OpenSearch or Bedrock Knowledge Bases projection |
| Runtime graph | Compiled typed relationships loaded in memory |
| Customer revisions and decisions | Existing DynamoDB workspace model |
| Change notifications | EventBridge events after release promotion |

Do not introduce Neptune in the MVP. Reconsider it only when compiled in-memory
traversal cannot meet measured impact-analysis or exploration requirements.

## 9. Repository Target

```text
knowledge/
  schemas/
    capability.schema.json
    offering.schema.json
    claim.schema.json
    decision-pattern.schema.json
    outcome-observation.schema.json
  sources/
    registry.yaml
  capabilities/
  components/
  offerings/
  interfaces/
  claims/
  decision-patterns/
  scenarios/

tools/knowledge/
  collect.py
  snapshot.py
  diff.py
  extract.py
  validate.py
  compile.py
  release.py
  impact.py

PlatformAdvisorAgent/app/PlatformAdvisorAgent/advisor_core/v3/catalogs/
  # Generated CatalogRelease outputs; no longer the primary authoring surface.
```

## 10. Ninety-Day Delivery Plan

### Phase 0: Stabilize The Existing Baseline, Days 1-5

- Freeze new domain, scoring, and assurance features.
- Fix the currently failing v3 tests.
- Record the current logical inventory and catalog hashes.
- Identify which existing rules represent hard constraints versus preferences.
- Mark current catalog JSON as authored legacy input pending migration.

**Exit:** Existing behavior is green, reproducible, and pinned as the migration
baseline.

### Phase 1: Semantic Foundation, Days 6-15

- Approve the eight entities and typed relationships.
- Define stable identifier, lifecycle, provenance, and freshness rules.
- Implement JSON schemas and OKF-compatible front matter.
- Create three complete capability pages with offerings and evidence.
- Define authority tiers and critical-claim review policy.

**Exit:** A reviewer can inspect one capability, see all implementation options,
trace every factual claim, and understand when each option is appropriate.

### Phase 2: Source Registry And Snapshots, Days 16-30

- Implement the source registry.
- Register the first 30-50 high-value sources.
- Build HTTP, RSS, GitHub release, and structured API collectors.
- Store immutable snapshots with normalized content and hashes.
- Detect structural changes and record collection health.

**Exit:** An authoritative source change produces a reproducible snapshot and a
machine-readable diff without modifying production knowledge.

### Phase 3: Extraction And Review, Days 31-45

- Extract atomic claim candidates with structured output.
- Propose typed relationships and affected capability IDs.
- Detect contradictions, missing scope, and stale superseded claims.
- Generate a Git pull request with source and diff context.
- Require human approval for critical product, security, compatibility, cost,
  and lifecycle claims.

**Exit:** A source change becomes a reviewable knowledge PR, and no agent can
publish directly.

### Phase 4: Compiler And Release, Days 46-60

- Validate schemas, IDs, references, effective dates, and evidence.
- Compile authored knowledge into the existing `CatalogRelease`.
- Generate deterministic release and content hashes.
- Run scenarios and hard-constraint safety tests.
- Sign and publish immutable release bundles.
- Produce release notes and a semantic release diff.

**Exit:** The same approved knowledge commit always produces the same signed,
tested catalog release.

### Phase 5: Runtime And Impact Analysis, Days 61-75

- Load a pinned compiled catalog in the v3 engine.
- Keep deterministic rules for hard eligibility, dependency, incompatibility,
  lifecycle, and required controls.
- Move subjective guidance into reviewed decision patterns.
- Calculate affected capabilities, offerings, rules, workspaces, and decisions.
- Add catalog-upgrade preview and explicit workspace reassessment.
- Add a "What changed and why it matters" workspace view.

**Exit:** A promoted product change can identify affected customer decisions
without silently changing their pinned architectures.

### Phase 6: Pilot And Outcome Loop, Days 76-90

- Run three end-to-end coding-platform architecture cases.
- Record decisions, alternatives, overrides, implementations, and deviations.
- Define a small outcome contract for cost, reliability, delivery, quality, and
  control verification.
- Ingest 30/60/90-day observations as evidence, not automatic truth.
- Convert disagreements and failures into reviewed scenarios, decision patterns,
  or explicit coverage gaps.

**Exit:** At least one implementation observation changes or confirms a
decision pattern through the normal reviewed release process.

## 11. Ordered Task Backlog

Task IDs are stable so they can be moved into GitHub Issues or another tracker.

### P0: Baseline And Governance

- [ ] **KS-001 - Freeze expansion work**
  - Pause new platform domains and nonessential scoring/assurance features.
  - Done when the team has an explicit 90-day scope and owner.

- [x] **KS-002 - Restore a green v3 baseline**
  - Resolve unknown-answer, question-ranking, delta, projection, assumption, and
    roadmap test drift.
  - Done when the focused v3 suite passes with no skipped release tests.
  - Verified 2026-08-11: focused v3 suite `104 passed`; frontend TypeScript
    check passed.

- [x] **KS-003 - Classify existing rules**
  - Label each rule `hard_constraint`, `compatibility`, `preference`, or
    `explanation`.
  - Done when preferences can be separated from deterministic authority.
  - Verified 2026-08-11: 24 hard constraints, 15 compatibility rules, and 1
    preference are compiler-enforced; focused v3 suite `109 passed`; frontend
    TypeScript check passed.

- [x] **KS-004 - Record migration baseline**
  - Persist catalog inventories, hashes, representative inputs, and outputs.
  - Done when future compilers can prove behavioral parity or explain changes.
  - Verified 2026-08-11: `knowledge/baselines/coding-platform-v3.json` pins the
    current catalog, representative requirements, architecture, feasibility,
    recommendation, assurance, and projection hashes; the release-safety parity
    test passes.

- [x] **KS-005 - Write authority ADR**
  - Document source, claim, ontology, engine, LLM, reviewer, and outcome
    authority.
  - Done when no component can ambiguously publish decision-grade knowledge.
  - Accepted 2026-08-11:
    `docs/adr/0001-knowledge-authority-boundaries.md` defines proposal, approval,
    publication, customer-decision, outcome, and fail-closed boundaries.

### P0: Semantic Model

- [x] **KS-010 - Approve entity schemas**
  - Implement the eight entity schemas and common metadata.
  - Depends on KS-005.
  - Verified 2026-08-11: immutable, discriminated Pydantic contracts cover
    capability, component, offering, variant, interface, claim, decision
    pattern, and outcome observation with shared lifecycle, freshness, and
    review metadata.

- [x] **KS-011 - Approve relationship vocabulary**
  - Define direction, cardinality, scope, provenance, and lifecycle semantics.
  - Depends on KS-010.
  - Verified 2026-08-11: ten relationship types enforce allowed entity kinds,
    direction, cardinality, scoped applicability, supporting claims, and
    canonical ordering for symmetric relationships.

- [x] **KS-012 - Define identifier rules**
  - Cover renames, aliases, merges, splits, supersession, and deletion.
  - Depends on KS-010.
  - Accepted 2026-08-11:
    `docs/adr/0002-stable-knowledge-identifiers.md` and validated identifier
    transitions preserve immutable IDs across rename, merge, split, supersede,
    and retire operations.

- [x] **KS-013 - Define claim scope**
  - Require provider, product, variant, version, region, configuration, effective
    date, source, reviewer, and freshness where applicable.
  - Depends on KS-010.
  - Verified 2026-08-11: every claim explicitly scopes provider, product,
    variant, version, region, and configuration as specified, universal, or not
    applicable; effective dates, evidence snapshots, review, and freshness are
    mandatory.

- [x] **KS-014 - Define source authority and review policy**
  - Specify which claim classes require one or two reviewers.
  - Depends on KS-005.
  - Accepted 2026-08-11:
    `docs/adr/0003-source-authority-and-claim-review.md` and executable claim
    policies enforce source-tier eligibility, corroboration, and reviewer
    counts.

- [x] **KS-015 - Author three reference capability pages**
  - Include execution isolation, tool gateway, and model routing.
  - Depends on KS-010 through KS-014.
  - Verified 2026-08-11: reviewed OKF-compatible Markdown/YAML pages for
    isolated execution, governed tool access, and model routing validate against
    the approved capability schema.

### P0: Source Collection

- [x] **KS-020 - Implement SourceRegistry schema**
  - Include owner, authority tier, cadence, collector, parser, terms, and health.
  - Verified 2026-08-11: immutable source registry contracts cover ownership,
    authority, collection cadence, collector/parser configuration, freshness,
    collection rights, enablement, tags, and operational health with fail-closed
    validation.

- [x] **KS-021 - Register the first source portfolio**
  - Add 30-50 Tier A and Tier B sources across three implementation ecosystems.
  - Depends on KS-020.
  - Verified 2026-08-11: the initial portfolio contains 40 schema-validated
    sources across AWS, GitHub, GitLab, and shared standards. All sources remain
    disabled pending explicit terms review.

- [x] **KS-022 - Implement HTTP and RSS collection**
  - Preserve headers, retrieval time, normalized body, and content hash.
  - Depends on KS-020.
  - Verified 2026-08-11: deterministic collectors preserve raw bytes, normalized
    content, headers, redirect URI, retrieval time, media type, and raw and
    normalized hashes with fail-closed status and size handling.

- [x] **KS-023 - Implement Git release collection**
  - Capture release, tag, changelog, commit, and security-advisory changes.
  - Depends on KS-020.
  - Verified 2026-08-11: GitHub collection captures releases, changelogs,
    annotated and lightweight tag targets, resolved commit identity, and
    repository security-advisory revisions in a deterministic snapshot.

- [x] **KS-024 - Implement immutable snapshot storage**
  - Store original and normalized artifacts without destructive overwrite.
  - Depends on KS-022 and KS-023.
  - Verified 2026-08-11: filesystem and S3 stores write raw, normalized, and
    manifest artifacts immutably, allow identical retries, reject conflicting
    overwrites, and verify content hashes before persistence.

- [x] **KS-025 - Implement structural diff**
  - Ignore navigation noise while preserving product, table, schema, and pricing
    changes.
  - Depends on KS-024.
  - Verified 2026-08-11: structure-aware comparison filters navigation,
    header, footer, script, and style noise while retaining headings, tables,
    schemas, code, pricing, and descriptive changes with explicit significance.

- [x] **KS-026 - Implement collection health**
  - Alert on access failure, parser failure, unexpected deletion, and overdue
    freshness.
  - Depends on KS-024.
  - Verified 2026-08-11: health assessment derives healthy, degraded, failing,
    paused, and never-checked states and emits warning or critical alerts for
    access, parser, deletion, and freshness failures.

### P0: Knowledge Review

- [x] **KS-030 - Define ClaimCandidate contract**
  - Separate extracted text, normalized claim, source locator, scope, confidence,
    and proposed relationships.
  - Depends on KS-013 and KS-025.
  - Verified 2026-08-11: untrusted candidates retain exact source text,
    normalized interpretation, structural locator, explicit scope, confidence,
    warnings, extractor identity, and proposed relationships without approval
    or publication authority.

- [x] **KS-031 - Implement structured extraction**
  - Use Bedrock structured output with no publication permission.
  - Depends on KS-030.
  - Verified 2026-08-11: Bedrock Converse requests use a JSON schema,
    explicitly bounded output tokens, adaptive production retries, trusted
    extractor metadata, optional pinned guardrails, and strict candidate
    validation with no repository or catalog publication dependency.

- [x] **KS-032 - Implement contradiction detection**
  - Compare active claims by semantic subject, predicate, scope, and time.
  - Depends on KS-030.
  - Verified 2026-08-11: conservative comparison detects conflicting scalar
    facts and positive/negative relationships only when subject, applicability,
    and effective periods overlap; multi-valued relationships and disjoint
    scopes do not produce false conflicts.

- [x] **KS-033 - Generate knowledge pull requests**
  - Include source diff, candidate claims, affected entities, and reviewer guide.
  - Depends on KS-031 and KS-032.
  - Verified 2026-08-11: deterministic review bundles generate PR metadata,
    source diffs, candidate files, affected-entity indexes, contradiction
    reports, and reviewer guides with immutable file hashes.

- [x] **KS-034 - Implement review states**
  - Support proposed, approved, rejected, superseded, stale, and disputed.
  - Depends on KS-014 and KS-033.
  - Verified 2026-08-11: append-only review records enforce optimistic
    concurrency, terminal states, replacement identity, and claim-class reviewer
    counts across all required states.

- [ ] **KS-035 - Prevent direct agent publication**
  - Enforce repository and pipeline permissions.
  - Depends on KS-033.
  - In-repo controls verified 2026-08-11: research agents may only write
    candidates and review bundles, human reviewers may only record review
    decisions, and the release pipeline may publish only approved knowledge
    with a non-blocking contradiction report.
  - Remaining external controls: configure real CODEOWNERS identities, protect
    the default branch, require knowledge-validation CI, and restrict release
    credentials to the publication pipeline.

### P0: Compiler And Release

- [x] **KS-040 - Build semantic validator**
  - Validate schemas, references, cycles, lifecycle, claim scope, and evidence.
  - Depends on KS-010 through KS-015.
  - Verified 2026-08-11: deterministic release validation rejects duplicate
    identities and aliases, missing or retired references, missing evidence,
    stale active knowledge, endpoint-kind mismatches, duplicate or conflicting
    edges, and active `REQUIRES` or `SUPERSEDES` cycles.

- [x] **KS-041 - Build OKF-to-CatalogRelease compiler**
  - Generate requirements, components, rules, offerings, interfaces, and claims.
  - Depends on KS-040.
  - Verified 2026-08-11: strict OKF Markdown loading feeds deterministic
    logical and deployable compilers. Approved semantic components, claims,
    offerings, variants, and interfaces are combined with typed runtime
    projection policy; corroborating evidence remains separately traceable and
    both existing catalog safety compilers validate the generated releases.

- [x] **KS-042 - Migrate current catalog knowledge**
  - Preserve current stable IDs or provide explicit migration aliases.
  - Depends on KS-041 and KS-004.
  - Verified 2026-08-11: the pinned logical and deployable catalogs translate
    into semantic entities, relationships, snapshots, and projection policy,
    then recompile with parity across 25 requirements, 44 components, 7
    patterns, 40 rules, 22 interfaces, 176 service variants, templates, and
    capability rules. The checked-in migration bundle is content-addressed and
    rejects tampering.

- [x] **KS-043 - Build release scenarios**
  - Cover positive, negative, unknown, stale, contradiction, and one-variable
    flip cases.
  - Depends on KS-041.
  - Verified 2026-08-11: the existing 24 deployment-family scenarios retain
    six positive, six rejection, six unknown, and six one-variable-flip cases;
    a declarative semantic release suite adds positive, missing-reference,
    missing-evidence, stale-claim, contradiction, and one-variable-flip gates.

- [x] **KS-044 - Produce deterministic release artifacts**
  - Generate manifest, content hashes, source inventory, compiler version, and
    benchmark report.
  - Depends on KS-041 and KS-043.
  - Verified 2026-08-11: release `1.0.0` contains deterministic logical and
    deployable catalogs, semantic validation, source inventory, and benchmark
    report. The manifest pins compiler and migration versions plus exact file
    hashes and sizes; immutable rewrites are idempotent and conflicting writes
    fail closed.

- [ ] **KS-045 - Sign and publish releases**
  - Publish immutable artifacts and verification metadata.
  - Depends on KS-044.
  - In-repo implementation verified 2026-08-11: asymmetric KMS signing targets
    the manifest digest, verification is explicit, and the S3 publisher requires
    release-pipeline authorization plus immutable conditional writes with
    optional KMS encryption.
  - Remaining environment work: provision the asymmetric signing key and
    versioned release bucket, restrict their policies to the release role, and
    publish release `1.0.0` with a retained receipt.

- [x] **KS-046 - Make generated catalogs read-only**
  - Prevent manual edits under the runtime catalog output path.
  - Depends on KS-042.
  - Verified 2026-08-11: generated releases are documented as immutable,
    conflicting local writes fail closed, checked-in artifacts are rebuilt and
    compared byte-for-byte in tests, and a path-scoped GitHub workflow runs the
    migration, catalog, release, and publication safety suites.
  - Repository administration must require the `Knowledge Release Validation`
    check on the protected default branch.

### P1: Projections And Runtime

- [x] **KS-050 - Generate typed runtime graph**
  - Compile adjacency indexes for dependency, compatibility, alternatives, and
    evidence traversal.
  - Depends on KS-041.
  - Verified 2026-08-11: active approved knowledge compiles into
    content-addressed nodes and edges, forward/reverse adjacency, per-type
    relationship indexes, and subject/edge evidence indexes. Release `1.1.0`
    pins the graph hash and preserves immutable release `1.0.0`.

- [x] **KS-051 - Generate search projection**
  - Index only approved claims and reviewed knowledge pages.
  - Depends on KS-041.
  - Verified 2026-08-11: approved current entities and claims compile into
    content-addressed search documents and a deterministic lexical inverted
    index. OKF page bodies contribute searchable terms; draft, retired, future,
    expired, and stale records are excluded. Release `1.2.0` pins the search
    projection hash.

- [x] **KS-052 - Generate vector projection**
  - Treat embeddings as rebuildable discovery infrastructure.
  - Depends on KS-041.
  - Verified 2026-08-11: approved search documents compile into deterministic,
    overlapping vector-input chunks with stable IDs and input hashes. The
    chunking and embedding profile identities are pinned while model output
    remains separately materialized, replaceable infrastructure. Release
    `1.3.0` includes the vector projection without storing vectors as authority.

- [x] **KS-053 - Load pinned releases in the engine**
  - Remove production dependence on demo catalog construction.
  - Depends on KS-045.
  - Verified 2026-08-11: FastAPI and AgentCore load the same immutable
    `coding-platform/1.3.0` release through a fail-closed runtime loader. The
    loader validates the configured manifest hash, complete file inventory,
    every artifact byte hash and size, benchmark results, semantic validation,
    internal graph/search/vector hashes, and logical/deployable catalog
    identity before evaluation. Lambda and AgentCore CodeZip build paths package
    the release and pin its version and manifest hash in environment
    configuration. Production request paths no longer call
    `build_demo_workspace`; customer packages and AgentCore revisions retain
    the knowledge-release and deployable-catalog hashes.

- [x] **KS-054 - Thin deterministic decision authority**
  - Retain only hard constraints, closure, eligibility, lifecycle, and required
    controls as deterministic rules.
  - Depends on KS-003 and KS-053.
  - Verified 2026-08-11: a centralized authority policy now restricts logical
    architecture mutation to `hard_constraint` rules and deployment-family
    rejection to `compatibility` rules. Catalog compilation rejects
    authoritative rules that depend on advisory rules. Matching preferences no
    longer add components or enter the authoritative decision trace. Weighted
    score, Pareto, and sensitivity outputs remain deterministic comparisons but
    produce an `advisory` comparison leader rather than an automatically
    selected bundle; assurance remains blocked on explicit bundle selection.
    Projection metadata declares the authoritative and advisory surfaces, and
    the frontend uses comparison language instead of recommendation language.

- [x] **KS-055 - Add decision-pattern retrieval**
  - Retrieve reviewed `recommended_when`, `avoid_when`, trade-offs, and evidence.
  - Depends on KS-051 and KS-052.
  - Verified 2026-08-12: five reviewed coding-platform decision patterns now
    compile into immutable knowledge release `1.5.0`. FastAPI and AgentCore
    attach deterministic, candidate-specific fit guidance containing use
    conditions, avoid conditions, trade-offs, review metadata, and cited
    evidence. The workspace surfaces the guidance during discovery and in the
    deployable-node inspector. Incomplete discovery is explicitly labeled as a
    provisional pattern and architecture draft rather than a selected
    recommendation. The focused Chromium contract passes at desktop and mobile
    viewports.

### P1: Change Impact And Workspace

- [ ] **KS-060 - Implement semantic release diff**
  - Compare entities, claims, relationships, scenarios, and decision patterns.
  - Depends on KS-044.

- [ ] **KS-061 - Implement impact traversal**
  - Identify affected capabilities, offerings, controls, rules, and workspaces.
  - Depends on KS-050 and KS-060.

- [ ] **KS-062 - Add catalog upgrade preview API**
  - Show changed feasibility, selections, evidence, controls, and rationale
    without mutating the workspace.
  - Depends on KS-053 and KS-061.

- [ ] **KS-063 - Add explicit workspace upgrade**
  - Require user acceptance and preserve the prior pinned release.
  - Depends on KS-062.

- [ ] **KS-064 - Build the change-impact UI**
  - Show what changed, source evidence, affected decisions, and recommended
    reassessment.
  - Depends on KS-062.

- [ ] **KS-065 - Add freshness and dispute indicators**
  - Prevent stale or disputed critical claims from appearing decision-ready.
  - Depends on KS-034 and KS-053.

### P1: Outcomes And Learning

- [ ] **KS-070 - Define OutcomeObservation schema**
  - Require metric, baseline, target, actual, window, denominator, evidence, and
    quality.

- [ ] **KS-071 - Link decisions to implementations**
  - Record selected offering variants, configurations, deviations, and owners.
  - Depends on KS-070.

- [ ] **KS-072 - Capture control verification**
  - Store test, evidence, result, exception, effectiveness, and expiry.
  - Depends on KS-071.

- [ ] **KS-073 - Capture cost and operational observations**
  - Include model, runtime, storage, network, human review, incidents, and
    support effort.
  - Depends on KS-071.

- [ ] **KS-074 - Build outcome review workflow**
  - Propose decision-pattern or scenario changes without automatic promotion.
  - Depends on KS-072 and KS-073.

- [ ] **KS-075 - Complete three pilot cases**
  - Each case must include context, alternatives, decision, implementation,
    deviation, verification, and outcome.
  - Depends on KS-063 and KS-074.

### P0/P1: Quality, Security, And Operations

- [ ] **KS-080 - Add ingestion security controls**
  - Defend against prompt injection, malicious content, oversized documents,
    archive bombs, secrets, and unsafe links.

- [ ] **KS-081 - Add source and artifact integrity**
  - Verify hashes, signatures where available, provenance, and release
    immutability.

- [ ] **KS-082 - Add tenant isolation tests**
  - Ensure proprietary outcomes never leak into public or cross-tenant
    projections.

- [ ] **KS-083 - Add license and usage policy**
  - Record collection permission, quotation limits, retention, and attribution.

- [ ] **KS-084 - Add pipeline observability**
  - Measure source health, freshness, extraction accuracy, review latency,
    release latency, and impact-analysis completeness.

- [ ] **KS-085 - Add disaster recovery**
  - Prove restoration of source registry, snapshots, Git knowledge, releases,
    indexes, and customer decision links.

## 12. First Two Sprints

### Sprint 1

1. KS-001 through KS-005.
2. KS-010 through KS-014.
3. KS-020.
4. Draft KS-015 for isolated execution.
5. Demonstrate one current offering claim traced to an immutable source snapshot.

### Sprint 2

1. Complete KS-015 for three capabilities.
2. KS-021 through KS-025.
3. KS-030.
4. Prototype KS-031 and KS-033.
5. Demonstrate: source change -> diff -> claim candidate -> Git PR.

## 13. Success Measures

By day 90:

- At least 30 authoritative sources are monitored.
- At least 30 logical capabilities have reviewed knowledge pages.
- Three implementation ecosystems have end-to-end offering coverage.
- Every decision-critical product claim has provenance and freshness.
- A source change produces a reviewable PR within one business day.
- A promoted release identifies affected customer workspaces.
- Existing workspaces remain pinned until an explicit upgrade.
- No ingestion agent can directly publish production knowledge.
- Three pilot decisions include implementation and outcome observations.
- At least one reviewed outcome changes or confirms a decision pattern.

The central product metric is not catalog size. It is the percentage of
decision-critical claims that are current, reviewed, traceable, and connected to
observed implementation outcomes.
