---
type: platform-component
title: Skills
description: reusable procedures
group: registry
tags: [registry, skills]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: probe
trigger: [skill-library, reusable-procedures, prompt-management, shared-agent-workflows]
decision-question: "How are reusable agent procedures packaged, versioned, and distributed across your developer population?"
---

Packaged know-how the agent loads on demand — "how we do migrations here",
"our PR checklist" — authored once, shared across agents. The defining
mechanical property: a skill's full body loads into context only when it's
actually invoked, not permanently, so a large library of skills costs
almost nothing until one is used.

## Decisions

**Who invokes a skill?**
- The agent decides automatically when it judges the skill relevant — skill
  descriptions load into context so the agent knows what's available, but
  full content loads only on actual invocation
- The user invokes explicitly (e.g. a slash-command-style trigger) —
  removes ambiguity about whether the agent will use it, at the cost of the
  user having to know it exists
- Both — automatic by default, with an explicit override available

**Skill governance?**
- Open — anyone contributes, fastest to grow the library, least vetted
- Curated — reviewed before being added to a shared/project-level location
- Risk-tiered — scanned for injected instructions, since a skill can
  request broad tool access for itself; review project-level skills before
  trusting the source, same posture as reviewing any other artifact
  checked into a repository before trusting it

**Scope?**
- User-level — available across all of one person's projects, not shared
  with a team
- Project-level — checked into version control, shared with everyone who
  works in that project; requires accepting a workspace-trust step before
  its tool-access grants take effect
- Plugin-packaged — bundled with other artifacts (agents, hooks, MCP
  servers) and distributed as a unit

## Principles

- Full content loads on demand, not permanently — this is the entire reason
  a large skill library stays cheap; don't design around always-loaded
  reference material when a skill can carry it instead
- Review a skill's declared tool-access grant before trusting it, same as
  reviewing any other repository content before trusting it — a skill can
  request broad tool access for itself
- Re-invoking a skill whose content hasn't changed shouldn't append a
  duplicate copy into context — the mechanism should recognize "already
  loaded, unchanged" and avoid the redundant cost

## Connects to

- Loaded from the [Registry / Catalog](registry.md)
- Vetted per [Provenance](provenance.md) before being trusted, especially
  for project- or plugin-scoped skills sourced from outside the org's own
  authoring

## Sources

- [Extend Claude with skills](https://code.claude.com/docs/en/skills) — checked 2026-08-12 — supports: on-demand content loading vs. always-loaded reference material as the defining cost tradeoff, descriptions loaded into context with full body loading only on invocation, project-scoped skills requiring workspace-trust acceptance before their tool-access grants apply, the explicit caution that a skill can grant itself broad tool access and should be reviewed before trusting a repository, deduplication of identical re-invoked skill content to avoid appending redundant copies
