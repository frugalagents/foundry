---
type: platform-component-group
title: External
description: systems the harness reaches outside itself, always via a gateway
group: external
tags: [external]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

The actual destinations reached through the [MCP Gateway](../gateway/mcpgw.md)
and [Model Gateway](../gateway/modelgw.md) — enterprise systems, the open
web, and model providers. None of these are ever reached directly; the
gateways are what enforce policy on the way there.

## Components

- [Enterprise Landscape](landscape.md) — Jira/GitHub/APIs/DBs. Written.
- [Web & Search](web.md) — external web, docs, search; the primary
  prompt-injection surface. Written.
- [Model Providers](providers.md) — frontier/self-hosted LLMs, residency. Written.
