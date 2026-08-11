# ADR 0003: Source Authority And Claim Review

**Status:** Accepted
**Date:** 2026-08-11
**Decision owners:** Knowledge governance and domain architecture owners

## Decision

Every claim declares a claim class, one or more immutable source snapshots, and
the authority tier of each source. Claim approval is validated against the
following policy:

| Claim class | Allowed tiers | Minimum reviewers | Additional rule |
|---|---|---:|---|
| Product fact | A | 1 | Critical facts require 2 |
| Compatibility | A | 2 | Used by deterministic feasibility |
| Pricing or quota | A | 1 | Critical facts require 2 |
| Security control | A or B | 2 | Must distinguish requirement from guidance |
| Decision guidance | A, B, C, or D | 1 | Cannot become a hard constraint directly |
| Comparative evidence | C | 1 | Requires at least two independent snapshots |
| Outcome evidence | D | 1 | Applies only to its recorded customer context |

Critical claims always require at least two reviewers regardless of class.

## Source Tiers

- **Tier A, decision authority:** official product documentation, APIs, release
  notes, pricing, quotas, availability, compliance documentation, and ratified
  specifications.
- **Tier B, operational guidance:** official reference architectures, samples,
  maintainer repositories, security frameworks, and observability standards.
- **Tier C, comparative evidence:** reproducible benchmarks, peer-reviewed
  research, and disclosed independent implementation studies.
- **Tier D, proprietary outcome evidence:** reviewed customer decisions,
  configurations, control results, incidents, cost, reliability, and outcomes.

Tier B guidance cannot override a Tier A product fact. Tier C cannot establish a
critical product fact. Tier D evidence cannot be generalized beyond its scope
without a separately reviewed decision pattern.

## Review Independence

Two-reviewer claims require two distinct reviewer identities. The author or
extraction agent is not a reviewer. At least one reviewer must be a designated
domain owner for compatibility and security-control claims.

The first implementation validates reviewer count and source-tier eligibility.
Role assignment and reviewer-domain ownership will be enforced by the review
workflow when the source registry is introduced.

## Consequences

Collection agents may propose any claim class, but inadmissible evidence or
insufficient review prevents approval and therefore prevents catalog
publication. Source rank, retrieval score, or model confidence never substitutes
for authority tier and human review.
