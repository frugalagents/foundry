---
type: platform-component
title: IDE
description: in-editor agent
group: surfaces
tags: [surfaces, developer-experience]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

The agent inside a code editor — inline edits, diffs, side-panel chat,
@-mentioning files with specific line ranges. This is the surface where a
developer is actively looking at code while the agent works, which shapes
what "review before it lands" means here specifically: the review happens
in the same window as the edit, not in a separate approval step.

## Decisions

**Where does the harness run for the IDE?**
- Local — low latency, uses local files directly, no network round-trip for
  file access
- Remote / managed — central control and audit, fits when policy requires
  every session to run somewhere governed rather than on a developer's own
  machine
- Hybrid — UI local, execution remote; keeps editor responsiveness while
  routing actual tool execution through governed infrastructure

**Review granularity before edits land?**
- Review-and-accept whole plans before execution starts — the extension
  supports reviewing and editing a plan before accepting it
- Auto-accept edits as they're made, review after — faster iteration, shifts
  the safety net to diff review rather than plan approval
- Per-file diff review — reviews land at file granularity rather than
  whole-plan or fully automatic

## Principles

- One harness core behind every surface — the IDE is a thin presentation
  layer over the same reasoning loop other surfaces use, not a separate agent
- Review-diff-then-apply as the safe default — editors are well suited to
  this because the diff view is native to the surface already
- Conversation history and multiple concurrent conversations (separate tabs/
  windows) should be supported — a developer working on more than one task
  shouldn't be forced into one linear thread

## Stack Options

**Local**
- Claude Code in VS Code — native extension with inline diffs, plan review
  before acceptance, and multiple concurrent conversations in separate tabs;
  the harness runs locally alongside the editor, matching this option.

## Connects to

- Same [Permission Engine](../harness/perms.md) enforcement point as every
  other surface
- Executes through whichever [sandboxing component](../exec/index.md) the
  platform has chosen for code execution

## Sources

- [Use Claude Code in VS Code](https://code.claude.com/docs/en/vs-code) — checked 2026-08-12 — supports: native IDE integration with inline diffs, @-mentioning files with line ranges, reviewing/editing plans before accepting them, auto-accept-edits mode, conversation history, multiple concurrent conversations in separate tabs/windows
