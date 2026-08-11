# ADR 0001: Knowledge Authority Boundaries

**Status:** Accepted
**Date:** 2026-08-11
**Decision owners:** Platform Advisor architecture and knowledge maintainers

## Context

Platform Advisor must continuously ingest changing product, protocol, security,
pricing, and implementation information without allowing an ingestion agent or
LLM to silently change decision-grade behavior.

The system also needs a clear distinction between:

- source material published by an external authority;
- atomic claims extracted from that material;
- provider-neutral semantic identity;
- deterministic feasibility behavior;
- preference and trade-off guidance;
- customer-specific decisions; and
- observed implementation outcomes.

Without explicit authority boundaries, retrieval results, generated summaries,
ontology changes, and customer observations can be mistaken for verified facts.

## Decision

Knowledge moves through explicit authority stages. No stage may assume the
authority of the next stage.

| Artifact or action | May propose | Must approve | Decision authority |
|---|---|---|---|
| Raw source snapshot | Collector | Automated integrity checks | Evidence only |
| Claim candidate | Extraction agent or maintainer | Assigned reviewer | None |
| Approved claim | Reviewer | Critical-claim reviewer when required | Product fact within its declared scope |
| Semantic entity or relationship | Agent or maintainer | Ontology owner | Provider-neutral identity and meaning |
| Decision pattern | Agent, architect, or outcome analyst | Domain architect | Soft guidance with cited evidence |
| Hard constraint or compatibility rule | Domain architect | Rule owner and release reviewer | Deterministic feasibility |
| Catalog release | Knowledge compiler | Release reviewer | Only published input accepted by the engine |
| Requirement patch | LLM, UI, or API client | Customer/user acceptance | Customer context only |
| Architecture revision | Decision engine | Deterministic validation | Customer design for its pinned catalog release |
| Outcome observation | Telemetry pipeline or user | Outcome owner | Evidence for later review, never an automatic rule |

## Non-Delegable Boundaries

1. An LLM may extract, summarize, classify, and propose. It may not publish an
   approved claim, semantic identity, hard rule, catalog release, or customer
   requirement.
2. Retrieval may find relevant knowledge. Retrieval rank is not decision
   authority.
3. A source snapshot proves what a source contained at a point in time. It does
   not prove that an extracted interpretation is correct.
4. A claim is authoritative only for its declared subject, predicate, object,
   version, region, edition, configuration, and validity interval.
5. Semantic relationships that affect feasibility must be backed by approved
   claims and compiled into a signed, immutable catalog release.
6. Customer overrides change only the customer workspace. They do not mutate
   shared knowledge.
7. Outcomes may generate claim or decision-pattern proposals. They may not
   automatically change shared recommendations or constraints.

## Rule Authority

Every decision rule must declare one of four authority classes:

- `hard_constraint`: a component-level requirement or exclusion that changes
  logical architecture and is enforced deterministically;
- `compatibility`: a deployment-pattern exclusion backed by compatibility
  evidence and enforced deterministically;
- `preference`: optional architecture guidance used for recommendation and
  explanation, not feasibility rejection;
- `explanation`: non-mutating rationale or warning.

The catalog compiler rejects invalid authority, effect, and target
combinations. The engine must never reinterpret a preference or explanation as
a hard constraint.

## Publication Workflow

```text
source registration
  -> immutable snapshot
  -> claim candidate
  -> review and approval
  -> semantic or decision-pattern proposal
  -> compiler validation
  -> release review
  -> immutable catalog release
  -> explicitly pinned customer workspace
```

Critical claims require:

- an authoritative source snapshot;
- an explicit reviewer;
- a scoped validity interval;
- a freshness policy;
- no unresolved contradiction with another active critical claim; and
- regression coverage for every hard rule they support.

## Fail-Closed Behavior

The compiler or release pipeline must reject publication when:

- referenced evidence is missing, unapproved, stale beyond policy, or outside
  the claim scope;
- identifiers or relationships are unresolved;
- critical claims contradict one another;
- a rule violates its declared authority class;
- representative migration baselines drift without an accepted change record;
  or
- release identity, content hash, or signature cannot be reproduced.

Unknown or disputed information remains unknown or disputed. It is not replaced
with an LLM inference.

## Consequences

The knowledge pipeline requires review queues, ownership, provenance, freshness,
and release controls. This adds publication friction, but it keeps collection
automation separate from decision authority and makes every customer
architecture reproducible against a specific catalog release.

The first semantic schemas and relationship vocabulary must encode these
boundaries directly rather than relying on documentation alone.
