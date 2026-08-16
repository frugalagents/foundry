---
type: platform-component
title: Registry / Catalog
description: approved building blocks
group: registry
tags: [registry, governance]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [enterprise-tool-catalog, tool-governance, multiple-teams, curated-toolset]
decision-question: "How will approved tools, MCP servers, and skills be catalogued, versioned, and governed across teams?"
---

The versioned source of truth for everything the harness may load — tools,
plugins, skills, subagents, MCP servers — plus who is entitled to use each.
Authors publish here; the harness composes from here at assembly time,
rather than loading arbitrary artifacts on demand. Concretely, this maps to
configuration scoping: which artifacts are available at which scope
(project vs. user vs. organization-managed), and — for anything sourced
externally, like an MCP server or a plugin — an explicit trust/approval step
before it's usable, not automatic loading on first reference.

## Decisions

**Catalog scope?**
- Org-wide — one source of truth, simplest to audit, least team autonomy
- Per-team — more autonomy, more sprawl, harder to audit centrally
- Federated — an org-level base catalog plus team-level extensions; scoping
  concretely maps to configuration precedence rules (e.g. local overrides
  project overrides user/org-wide, or the reverse, depending on what you
  want to be overridable)

**Publish workflow?**
- Self-serve + automated scan — fast, relies entirely on the scan catching
  problems
- Security review gate — safer, slower; matches the general pattern of
  requiring explicit approval before an externally-sourced artifact (an MCP
  server, a plugin) is usable, rather than trusting it on first reference
- Risk-tiered — read-only artifacts auto-approved, write-capable ones
  reviewed; ties directly to [Tools & Plugins](tools.md)'s read/write
  separation

**Entitlements?**
- Role-based — team/role maps to allowed catalog entries
- Per-agent grants — explicit, doesn't scale past a handful of agents
- Env-scoped — dev vs. prod catalogs differ, needed once agents can reach
  production systems at all

## Principles

- Nothing loads unless published and entitled — no artifact is available to
  the harness just because it exists on disk somewhere in scope
- Version-pin, with a central kill-switch on compromise — an entry can be
  disabled catalog-wide without every consumer having to notice and react
  individually
- Every artifact sourced from outside the org's own authoring (a third-party
  MCP server, an externally-authored skill/plugin) needs an explicit
  trust/approval step before use — never auto-load an external artifact on
  first reference. See [Provenance](provenance.md) for the supply-chain
  vetting this implies.

## Connects to

- Feeds [Tools & Plugins](tools.md), [Skills](skills.md),
  [Subagents](subagents.md), and [MCP Servers](mcpservers.md) — this
  component is the catalog they're all pulled from
- Vetted per [Provenance](provenance.md) before publication
- Governed by the same [Identity & Access](../access/identity.md) model for
  entitlements

## Sources

- Verify against current docs — this file describes the general registry/
  catalog *pattern* (scoping, approval-before-use, kill-switch) rather than
  one specific product's implementation; no single citable source covers
  the pattern as a whole the way more concrete components in this batch
  have one. The scoping-precedence and approval-before-use claims are
  corroborated indirectly by [MCP Servers](mcpservers.md)'s and
  [Skills](skills.md)'s own sources, which describe the concrete mechanism
  for those two artifact types specifically.
