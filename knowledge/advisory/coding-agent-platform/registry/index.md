---
type: platform-component-group
title: Registry
description: catalog and supply-chain trust for everything the harness loads
group: registry
tags: [registry]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Everything the harness may load — tools, plugins, skills, subagents, MCP
servers — is catalogued and entitled here, and vetted for provenance before
it's trusted. 6 components: 5 from the original taxonomy plus
[Provenance](provenance.md), a net-new addition (see `ARCHITECTURE.md` §2.3,
gap audit item 4).

## Components

- [Registry / Catalog](registry.md) — scoping, publish workflow, entitlements. Written.
- [Tools & Plugins](tools.md) — file/shell/git/search, granting model. Written.
- [Skills](skills.md) — reusable procedures, on-demand loading. Written.
- [Subagents](subagents.md) — delegated specialists, depth/fan-out caps. Written.
- [MCP Servers](mcpservers.md) — integration connectors, approval model. Written.
- [Provenance](provenance.md) — supply-chain vetting before install. Written (net new).
