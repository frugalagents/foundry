---
type: platform-component
title: Memory
description: cross-session persisted facts, distinct from task context
group: harness
tags: [harness, memory]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Facts the agent remembers *across* sessions — user preferences, project
facts, summaries of past work — as distinct from [Context](context.md),
which is what the agent sees within the current task only. Concretely,
short-term memory (turn-by-turn events within one session) and long-term
memory (insights extracted and persisted across sessions via strategies)
are commonly separately configured and separately billed, because they
have genuinely different governance implications: "remembers this user's
preferences forever" carries PII/residency questions that "keeps the
current file tree in context" does not.

This is a split of the original taxonomy's single "Context & Memory"
component (see `ARCHITECTURE.md` §2.3, gap audit item 2) — see
[Context](context.md) for the task-scoped half.

## Decisions

**Memory across sessions?**
- Stateless — fresh each task, no cross-session memory at all
- Short-term only — turn-by-turn events persist within a session (so a
  session can pause/resume) but nothing carries to a *different* session
- Short-term + long-term — long-term strategies extract durable facts
  (semantic facts, conversation summaries, user preferences, episodic
  memories) from short-term events and persist them across sessions

**Which long-term strategies, if any?**
- Semantic — extracts facts/knowledge as retrievable vectors
- Summarization — conversation summaries rather than raw facts
- User preference — captures preferences/settings specifically
- Episodic — stores episode-level memories, optionally with reflections
- More than one strategy can run simultaneously over the same underlying
  events; they aren't mutually exclusive

**Retention?**
- Fixed event expiry (e.g. 30 days) — short-term events age out
  automatically rather than accumulating indefinitely
- Indefinite — no automatic expiry; requires an explicit deletion/retention
  policy elsewhere if data-residency rules require one

## Principles

- Treat retrieved memory content as untrusted input, same as any other
  stored/user-generated content — it originated from past events and
  extraction output, not from a verified source, and should not be
  executed or evaluated directly
- Long-term memory's governance implications (PII, residency, "who can see
  what a past session remembers about them") are a different risk surface
  than task context's — don't reuse Context's access model unexamined for
  Memory
- Namespace memory records per actor/session so one user's or one
  tenant's long-term facts can't leak into another's retrieval — this is
  the cross-session analogue of Context's never-mix-tenants principle

## Connects to

- Distinct from, and configured separately from, [Context](context.md)
- Governed by the same [Identity & Access](../access/identity.md) model for
  which actor/session a memory record belongs to
- Retrieved content passes through the same untrusted-input handling as
  anything from [Web & Search](../external/web.md)

## Sources

- [AgentCore Memory guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/) — checked 2026-08-12 (fetched live via the bedrock-agentcore MCP server's memory guide; no single stable public URL captured for this specific page — flag for a follow-up Tier A source once a docs URL is confirmed) — supports: short-term (event-based) vs. long-term (strategy-extracted) memory as separately configured concepts, four built-in long-term strategies (semantic, summarization, user preference, episodic) usable in combination, namespace-based scoping per actor/session, configurable event expiry (3–365 days), and the explicit security guidance that retrieved memory content is untrusted input and should not be executed/evaluated directly
