---
type: platform-component
title: Standards Injection
description: org coding standards and compliance rules delivered into every agent session
group: knowledge-layer
tags: [knowledge-layer, standards, coding-standards, system-prompt, context-injection]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [coding-standards, architectural-rules, compliance-rules, enforce-standards, style-guide]
decision-question: "How will org-wide coding standards and compliance rules be delivered into every agent session without requiring developers to manually include them?"
---

Standards injection delivers coding standards, architectural patterns, and
compliance rules into the agent's context at session start — so the agent
applies org patterns by default, not generic best practices. It is the
distribution mechanism for standards, not the governance mechanism (that
lives in [Guardrails & Policy](../access/guardrails.md)).

## Delivery Mechanisms

**CLAUDE.md / system prompt (simplest)**
A project-level CLAUDE.md or operator system prompt contains your standards.
Every session loads it automatically. Good for stable, short content (< a few
hundred tokens per session). Zero extra infrastructure.

**Retrieval-based injection (RAG over standards docs)**
Standards are stored in a knowledge base — separate from the code intelligence
index — and retrieved at task start based on what the agent is working on.
Good for large standards libraries where full injection on every session is too
expensive. A backend change or API standards doc is only injected for sessions
working in that area.

**Tool call at session init**
The harness calls a `get-standards` tool at session start that returns relevant
rules as a tool result. Useful when standards must be versioned and
change-managed independently of system prompt content, or when standards are
generated dynamically based on the task context.

## Decisions

**Delivery mechanism?**
- CLAUDE.md / system prompt for small, stable org-wide rules (< 500 tokens)
- RAG injection for large libraries or domain-specific standards
- Both: core rules in system prompt, domain rules retrieved on demand

**How are standards kept current?**
- Manual update to CLAUDE.md — simple; risks staleness; acceptable for slow-
  changing orgs
- Versioned standards in a knowledge base re-indexed on change — better
  freshness, more infrastructure; recommended for orgs with active standards
  governance

**Who owns and approves standards changes?**
- Platform team — central authority, consistent enforcement
- Guild / practice leads — distributed domain-expert ownership; needs
  coordination to prevent contradictory standards across guilds

**What happens when agent output violates a standard?**
- Guardrail catch (output filtering rule) — hard enforcement; catches the
  violation before the developer sees the output
- Advisory only — agent notes the standard; human reviews; softer, relies
  on code review to catch misses
- Both is common: use guardrails for security/compliance rules, advisory for
  style preferences

## Stack Options

**CLAUDE.md / system prompt (zero infra)**
- Claude Code CLAUDE.md — committed to the repository root; automatically
  loaded into every Claude Code session in that project; no infrastructure;
  version-controlled with the codebase; the lowest-friction mechanism for
  stable, short standards
- Operator system prompt (Claude Code enterprise) — set centrally via the admin
  console; applies to all sessions regardless of repo; cannot be overridden by
  per-repo CLAUDE.md; use for org-wide non-negotiables

**Retrieval-based injection (AWS managed)**
- Amazon Bedrock Knowledge Bases — store standards documents as a separate
  knowledge base (not mixed with code intelligence); retrieve at task start
  using the Retrieve API with metadata filtering (e.g., "language=python",
  "domain=payments"); charged per retrieval query, not per session

**Retrieval-based injection (open source)**
- LlamaIndex with any vector store — build a standards retrieval pipeline
  alongside the code intelligence pipeline; query both at task start and
  merge the results into the context window
- pgvector (small-scale) — store standards embeddings in the same Postgres
  instance as code embeddings with a `type='standards'` column; single
  infrastructure footprint

**Tool-call injection (versioned delivery)**
- Lambda-backed MCP tool `get-standards` — the harness calls this tool at
  session init; the Lambda reads from a versioned S3 object or Parameter Store;
  standards are updated by pushing a new object version; no session restart
  needed; audit trail of which version was injected per session
- AWS Systems Manager Parameter Store — store short standards strings as
  versioned parameters; the tool reads the current version at call time;
  free tier covers most org sizes; simple change management via Parameter
  Store version history

## Principles

- Standards injection should be invisible to the developer — a platform
  guarantee that the agent already knows the rules, not a prompt they must
  add manually
- Token cost scales: N developers × M sessions/day × standard length = real
  cost input; keep injected content concise and retrieved content precise
- Version standards content the same way you version code: change history,
  review process, rollback — a standards change that breaks every developer's
  workflow needs a rollback path
- Injection and enforcement are distinct levers: injection shapes the agent's
  default behaviour; guardrail rules enforce hard constraints regardless of
  whether the agent was "told" the standard

## Connects to

- [Context](../harness/context.md) — injected standards consume context window
  budget; account for standard length in context sizing decisions
- [Guardrails & Policy](../access/guardrails.md) — hard standard violations
  enforced via output filtering, not just injection
- [Org Knowledge](org-knowledge.md) — extraction results feed new standards
  candidates into this pipeline; extraction discovers, injection distributes
- [Registry / Catalog](../registry/registry.md) — the standards delivery
  mechanism (knowledge base, tool) is a governed platform component
