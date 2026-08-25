---
type: platform-component-group
title: Surfaces
description: developer-facing entry points into the harness
group: surfaces
tags: [surfaces]
timestamp: 2026-08-12T00:00:00Z
status: candidate
decision-domain: surface_strategy
priority: 4
implies: [surfaces/ide, surfaces/cli, surfaces/chat, surfaces/ci, surfaces/jupyterlab]
---

Where a developer or a system event actually engages the agent. All four
surfaces sit on top of the same harness core — the differences are in trust
model, trigger mechanism, and how much a human is present in the loop, not in
the underlying reasoning loop itself.

## Components

- [IDE](ide.md) — in-editor agent, inline diffs, plan review. Written.
- [CLI / Terminal](cli.md) — interactive + headless/scripted mode. Written.
- [Chat / PR Bot](chat.md) — async, mention-triggered or automation-mode. Written.
- [CI/CD Trigger](ci.md) — agent invoked by pipeline events/schedules. Written.
