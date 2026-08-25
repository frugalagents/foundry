---
type: platform-component
title: Context
description: repo · rules · compaction — task-scoped, this session only
group: harness
tags: [harness, context]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: probe
trigger: [context-window-management, repo-context, large-codebase, context-compaction]
decision-question: "How is in-session context loaded, compacted, and scoped to the task — and what stays out of the window?"
decision-domain: context_strategy
priority: 6
requires: [harness/runtime]
---

How the agent sees your code during a task — pulls the right files,
symbols, history, and standards into the working set, and compacts as it
fills so it never runs out of room. Rules (CLAUDE.md-style project
conventions) load here. This component is task-scoped and session-local by
definition — cross-session persistence of facts is a distinct concern,
covered by [Memory](memory.md).

This is a split of the original taxonomy's single "Context & Memory"
component (see `ARCHITECTURE.md` §2.3, gap audit item 2) — task context and
cross-session memory are separately configured, separately governed
(different PII/residency implications), and often separately billed, so
treating them as one component understated a real design decision.

## Decisions

**Context sourcing?**
- On-demand read + grep — always fresh, no index to keep in sync, costs a
  tool round-trip per lookup
- Index / code graph — fast recall at scale, requires building and
  maintaining the index
- Retrieval (RAG) — needed for large or cross-repo context that won't fit
  in a working set built from on-demand reads alone

**Compaction strategy?**
- Reactive — only compact when the context window actually overflows
- Proactive — compact before hitting the limit, at a configured usage
  threshold, so a large single turn doesn't hit a hard failure mid-call
- Both — proactive as the default behavior, reactive as the fallback if
  proactive compaction wasn't enough

## Principles

- Compact aggressively; retrieve on demand — don't keep everything in
  context just because it was relevant once
- Never mix another tenant's context into a session — this is a hard
  boundary, not a best-effort one, especially once Memory (cross-session)
  is layered on top and could otherwise leak facts across tenants
- Rules/conventions files should be loaded once per session as a stable,
  cacheable prefix — reloading them per-turn wastes the same tokens
  repeatedly for content that didn't change

## Connects to

- Distinct from, and a prerequisite input alongside, [Memory](memory.md) —
  this component is what the agent sees *this task*; memory is what
  persists *across* tasks
- Consumed by the [Agent Loop](loop.md) on every turn

## Sources

- [strands.agent.conversation_manager.sliding_window_conversation_manager](https://strandsagents.com/docs/api/python/strands.agent.conversation_manager.sliding_window_conversation_manager/index.md) — checked 2026-08-12 — supports: proactive compaction at a configurable usage threshold (default 70%) as distinct from reactive-only overflow recovery, and truncating large tool results (preserving first/last N characters) before falling back to trimming whole messages — this corroborates the reactive-vs-proactive compaction decision above, though it describes one SDK's mechanism, not a cross-vendor claim
- Verify against current docs for the context-sourcing decision (on-demand
  vs. indexed vs. RAG) — no single citable source covers that half of this
  component yet; described here as a general pattern.

