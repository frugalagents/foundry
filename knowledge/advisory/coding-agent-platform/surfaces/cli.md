---
type: platform-component
title: CLI / Terminal
description: interactive + headless
group: surfaces
tags: [surfaces, automation]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Terminal surface for power users and scripting — the same harness as every
other surface, but with a non-interactive ("headless" / "print") mode built
specifically for automation: process a query and exit without waiting for
user input, rather than holding an open interactive session.

## Decisions

**Primary CLI mode?**
- Interactive — developer in the loop, conversational back-and-forth in the
  terminal
- Headless — invoked as `claude -p "query"`, processes and exits; designed
  for scripting, CI/CD pipelines, and programmatic usage rather than a human
  watching the session live

**Headless output format?**
- Plain text (default) — simplest for basic scripting
- Structured JSON — for programmatic parsing of the response
- Streaming JSON events — for real-time processing or verbose event-level
  detail

**Budget/turn controls for unattended runs?**
- No cap — acceptable only when the invocation is already tightly scoped
- Max spend cap — stops the run once a dollar ceiling is hit
- Max turn cap — stops the run once a number of agentic iterations is hit,
  exiting with an error rather than continuing silently

## Principles

- Headless mode must be fail-safe — an unattended run has no human to catch
  a runaway loop, so the budget/turn caps above are not optional in that mode
- Hard token / time budget per invocation, enforced at invocation time, not
  discovered after the fact
- Non-interactive permission handling (e.g. routing permission prompts to an
  MCP tool instead of blocking on a human) is a distinct decision from the
  interactive mode's default prompt-and-wait behavior — don't assume the same
  permission UX works unchanged in headless mode

## Connects to

- Same [Permission Engine](../harness/perms.md) as other surfaces, but must
  resolve every prompt without a human present
- Session persistence for headless runs can be disabled entirely — ties into
  [Memory](../harness/memory.md)'s session-scope decision

## Sources

- [Claude Code Print Mode (-p / --print)](https://code.claude.com/docs/en/cli-reference) — checked 2026-08-12 — supports: headless/print mode invocation syntax, three output formats (text/json/stream-json), `--max-budget-usd` spend cap, `--max-turns` iteration cap (exits with error when reached), `--permission-prompt-tool` for non-interactive permission handling, `--no-session-persistence` flag
