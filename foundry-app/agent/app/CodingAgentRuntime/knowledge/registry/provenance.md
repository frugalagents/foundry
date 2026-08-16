---
type: platform-component
title: Provenance
description: supply-chain security for tools, skills, and MCP servers
group: registry
tags: [registry, security, supply-chain]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: probe
trigger: [supply-chain-security, tool-signing, audit-trail, who-approved-this-tool]
decision-question: "How is the integrity and origin of tools, skills, and MCP servers verified before use?"
---

Pre-install-time vetting for anything the registry catalogs that wasn't
authored in-house — signing, provenance tracking, and dependency-pinning for
third-party tools, skills, and MCP servers. This is orthogonal to both
[Registry / Catalog](registry.md) (which catalogs and scopes artifacts, but
doesn't itself establish trust) and [Guardrails & Policy](../access/guardrails.md)
(which enforces runtime policy on calls, after an artifact is already
installed). Provenance is what decides whether an artifact should be
installable at all.

This component did not exist in the platform's original architecture diagram
— added after a gap audit found no home for supply-chain vetting anywhere in
the original 25-component taxonomy (see `ARCHITECTURE.md` §2.3). Status is
`candidate` pending Tier C corroboration.

## Decisions

**What gets vetted before install?**
- Every third-party artifact, regardless of source — strictest, highest
  friction
- Only write-capable / broad-tool-access artifacts — ties to
  [Tools & Plugins](tools.md)'s read/write separation; a read-only artifact
  is lower risk and may warrant lighter vetting
- Only artifacts from outside a pre-approved set of sources (e.g. official
  vendor servers) — narrower scope, relies on the source list itself being
  trustworthy and kept current

**Vetting mechanism?**
- Automated scan for injected instructions / suspicious patterns — cheap,
  catches known patterns, won't catch everything
- Human security review — slower, catches what a scan can't reason about,
  doesn't scale to a large or fast-growing catalog
- Both, risk-tiered — automated scan as a first pass, human review gated on
  what the scan flags or on artifact risk tier

**What happens after an artifact is approved?**
- Version-pinned, no auto-update — an update is a new artifact requiring
  its own vetting pass, not an automatic carry-forward of prior approval
- Central kill-switch on later-discovered compromise — approval isn't
  permanent; an artifact can be pulled catalog-wide if it's later found
  compromised, without requiring every consumer to individually notice and
  react

## Principles

- An artifact is untrusted until vetted, not trusted until proven otherwise
  — the default posture is exclusion, not inclusion
- Approval is a point-in-time judgment about a specific version, not a
  standing grant that survives an update unexamined
- Vetting for tools/skills/MCP servers all follows the same underlying
  concern (does this artifact request more capability or reach than its
  stated purpose needs, and could it smuggle instructions to the model) —
  don't design three separate vetting processes when one applies across all
  three artifact types

## Connects to

- Gates what may be published into the [Registry / Catalog](registry.md)
- Applies to [Skills](skills.md) and [MCP Servers](mcpservers.md)
  specifically as the trust step both of those files reference

## Sources

- Verify against current docs — no Tier A/C source captured yet for this
  component specifically. The *need* for this vetting step is corroborated
  indirectly by [Skills](skills.md)'s and [MCP Servers](mcpservers.md)'s own
  sources, which each independently warn about the same underlying risk
  (an artifact requesting broad tool access, or fetching external content
  that carries prompt-injection risk) without prescribing a single
  cross-artifact vetting mechanism. Do not assert a specific vendor's
  vetting process here until a real citation is on file — concrete
  candidate for the Tier C case-study sweep (see `ARCHITECTURE.md` §5).
