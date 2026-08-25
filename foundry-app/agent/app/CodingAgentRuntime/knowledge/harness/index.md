---
type: platform-component-group
title: Harness
description: the core agent loop and everything it directly depends on
group: harness
tags: [harness]
timestamp: 2026-08-12T00:00:00Z
status: candidate
decision-domain: harness_runtime
priority: 4
implies: [harness/runtime, harness/loop, harness/perms, harness/context, harness/memory, harness/rollback]
---

The agent's core reason-act-observe cycle and its immediate dependencies:
what it's allowed to do, what it can see, how it invokes tools, and how its
edits can be undone. 6 components — 2 (`context`, `memory`) are a split of
what was originally one component; `rollback` is net new (see
`ARCHITECTURE.md` §2.3).

## Components

- [Agent Loop](loop.md) — reason / act / observe cycle. Written.
- [Permission Engine](perms.md) — allow / deny / ask per tool call. Written.
- [Context](context.md) — task-scoped repo/file context for the current session. Written.
- [Memory](memory.md) — cross-session persisted facts, split from Context
  (see gap audit item 2). Written.
- [Tool Runtime](runtime.md) — invokes tools/subagents, dispatches to gateways. Written.
- [Rollback & Change Safety](rollback.md) — undo/diff/branch agent edits
  cheaply. Written (net new, gap audit item 3).
