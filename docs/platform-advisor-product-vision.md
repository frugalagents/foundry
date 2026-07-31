# Platform Advisor Product Vision

**Status:** Governing product vision
**Date:** 2026-07-30
**Scope:** Enterprise agentic coding-platform architecture

## Vision

Build an architecture-first workspace that behaves like a platform architect in
software.

The product starts with a clean, provider-neutral logical architecture organized
across platform planes. It does not start with an empty chat or a long
questionnaire. Chat gathers requirements, resolves trade-offs, and records
decisions while the architecture changes visibly beside it.

As requirements become known, the advisor must:

1. Confirm, reject, add, remove, or modify logical components.
2. Show assumptions, unresolved decisions, and rejected alternatives.
3. Refine deployment topology, trust boundaries, operating model, and controls.
4. Map provider-neutral components to compatible AWS, open-source, SaaS, and
   bring-your-own-platform implementations.
5. Explain how each answer changes architecture, security, operability,
   portability, token economics, and expected outcomes.
6. Ask only questions that can materially change feasibility, topology,
   components, controls, service selection, or ranking.

The canvas is the primary experience. Chat is the architecture co-design
interface. The deterministic decision engine is the authority for feasibility,
dependencies, compatibility, and traceability. Language models may extract
requirements and explain decisions; they may not silently invent facts, weaken
constraints, or select unsupported architecture.

## Final Customer Package

Every completed engagement should produce a versioned, replayable package:

- Customer-specific logical architecture.
- Deployable physical architecture and environment topology.
- Selected solution stack and configuration profiles.
- Feasible and rejected alternatives.
- Decision and trade-off matrices.
- Security, reliability, governance, and operational best practices.
- Token economics, capacity assumptions, and cost ranges.
- Outcome-based observability and evaluation model.
- Implementation roadmap, dependencies, milestones, and exit criteria.
- Requirements, assumptions, evidence, risks, controls, and decision trace.
- Infrastructure and policy artifacts where generation is safe and supported.

## Knowledge Moat

The moat is not a vector index or a collection of documents. It is a governed,
versioned architecture-intelligence system connecting:

```text
enterprise context
 -> requirement
 -> decision rule
 -> architecture pattern and overlay
 -> capability and component
 -> implementation offering and compatibility
 -> threat, control, and verification
 -> decision and implementation
 -> cost, incident, and outcome
```

Public documentation supplies evidence and candidate facts. Proprietary value
accumulates through normalized ontology, compatibility rules, decision
boundaries, independently reviewed scenarios, customer decisions,
implementation deviations, verification results, and measured outcomes.

Retrieval-augmented generation may help find and explain source material. It is
not the decision engine or the system of record.

## Product Principles

1. Architecture first; questions refine a visible hypothesis.
2. Progressive disclosure; ask the minimum high-information question.
3. Provider-neutral decisions before product mapping.
4. Deterministic feasibility before probabilistic explanation.
5. Evidence-backed claims and explicit freshness.
6. Alternatives and disqualifiers, not one opaque recommendation.
7. Controls count only when implementation and verification are defined.
8. Economics measure cost per successful outcome, not tokens alone.
9. Every decision is versioned, traceable, and replayable.
10. Customer outcomes continuously improve patterns and rules.
