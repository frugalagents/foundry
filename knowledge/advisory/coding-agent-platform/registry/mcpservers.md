---
type: platform-component
title: MCP Servers
description: integration connectors
group: registry
tags: [registry, mcp, integrations]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

The MCP servers the harness may connect to — each wrapping an external
system (an issue tracker, a database, an internal API). Registered here,
reached at runtime through the [MCP Gateway](../gateway/mcpgw.md). A server
that fetches external content on the agent's behalf is a real prompt-
injection surface — trust needs to be established before connecting, not
assumed by default.

## Decisions

**Who hosts MCP servers?**
- Vendor servers for common systems — someone else maintains the
  integration
- Custom for proprietary internal APIs — necessary for anything not
  already covered by a vendor server
- Mix, behind the gateway — the gateway is the uniform chokepoint
  regardless of who wrote the server

**Configuration scope?**
- Project-scoped, checked into version control — shared with the whole team
  working in that project
- User-scoped — available across one person's projects, private to them
- Organization-managed — deployed centrally, not something an individual
  project or user configures themselves

**Approval model?**
- Interactive approval prompt on first use — the default posture; a
  project-scoped server someone else added stays pending until a human
  reviews and approves it
- Auto-connect in unattended/headless runs — necessary for automation, but
  means the approval gate that exists in interactive sessions doesn't apply
  there; anything that shouldn't auto-connect unattended needs to be
  explicitly excluded rather than relying on the interactive prompt to
  catch it

## Principles

- Every server registered, signed/attributable, and versioned — nothing
  connects to an ad hoc, unregistered endpoint
- Reached only via the [MCP Gateway](../gateway/mcpgw.md) — never a direct
  connection from the harness to the server
- Verify trust before connecting any server that fetches external content —
  that's a real prompt-injection surface, not a hypothetical one
- **Headless/unattended sessions skip the interactive approval prompt
  entirely** — a server pending approval in an interactive session loads
  without asking in a headless run. If a server shouldn't be usable in
  unattended automation, it must be explicitly excluded (not merely
  "unapproved"), since the approval gate that would normally stop it isn't
  present in that mode.

## Stack Options

**Configuration scope (project/user/organization-managed)**
- Claude Code — three real configuration scopes: local (`~/.claude.json`,
  private to one project+user), project (`.mcp.json`, checked into version
  control), and user (`~/.claude.json`, cross-project, private to the
  account). No separate "organization-managed" scope exists client-side;
  centralized control is via managed settings distributed to teams instead.

**Approval model**
- Claude Code — interactive approval prompt on first use for project-scoped
  servers (`claude mcp list`/`claude mcp get` show pending approval); explicit
  opt-out via `disabledMcpjsonServers` for anything that must never
  auto-connect, since headless/print-mode/SDK sessions skip the prompt
  entirely.

## Connects to

- Reached exclusively through the [MCP Gateway](../gateway/mcpgw.md)
- Loaded from the [Registry / Catalog](registry.md)
- Vetted per [Provenance](provenance.md) before being trusted — an
  unsigned or unreviewed MCP server is an arbitrary-code-execution-adjacent
  risk before any runtime policy ever runs

## Sources

- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) — checked 2026-08-12 — supports: explicit trust-before-connecting guidance for servers that fetch external content (named prompt-injection risk), three configuration scopes (local/project/user) with project-scoped servers requiring an interactive approval prompt before use, and the specific caveat that headless/unattended runs (print mode, SDK sessions, cloud sessions) load project-scoped servers without showing that approval prompt — a server must be explicitly disabled to be excluded from those modes
