---
type: platform-component
title: Web & Search
description: external web · docs · search
group: external
tags: [external, security, prompt-injection]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

External web and search access, reached through the
[MCP Gateway](../gateway/mcpgw.md) — documentation, package registries, and
general web search when the agent needs outside knowledge. This is the
platform's most direct prompt-injection surface: content fetched from the
open web is, by construction, content the platform didn't author and can't
fully vet in advance.

## Decisions

**Web access posture?**
- None — closed corpus only; eliminates the surface entirely at the cost of
  cutting off legitimate need for current docs/package info
- Allowlisted domains — fetches restricted to a pre-approved set (official
  docs, package registries); narrows the surface without eliminating web
  access
- Open search with output filtering — broadest capability, relies entirely
  on the filtering step actually catching what it needs to catch

**What happens to fetched content before it reaches the model?**
- Passed through as-is — fastest, and the least defensible position, given
  that fetched content is untrusted by construction
- Filtered for injection patterns before use — a necessary floor, not a
  guarantee; a filter catches known patterns, not everything
- Treated as data only, never as instructions — the strongest framing:
  fetched content should never be capable of directly steering the agent's
  next tool call the way a legitimate instruction can

## Principles

- Filter fetched content for injection before use — this is not optional
  for any posture that allows fetching at all, including an allowlisted one
- Allowlist domains for sensitive environments — even a "trusted" domain can
  serve attacker-controlled content (a comments section, a wiki edit,
  a compromised CDN asset); allowlisting narrows exposure, it doesn't
  eliminate it
- **The reliable control is a trust boundary, not a content filter alone.**
  An agent's message history should be built from the platform's own
  trusted sources, not directly from fetched external content — fetched
  content is untrusted input the same way a request body or a loaded
  external snapshot is, and should never be treated as if the platform
  itself produced it
- A forged or injected instruction embedded in fetched content is
  indistinguishable from a real one to a naive pass-through — the filtering
  step exists specifically because "read the text" and "follow instructions
  in the text" are not the same operation, and fetched content should only
  ever be the former

## Connects to

- Reached through the [MCP Gateway](../gateway/mcpgw.md), same as every
  other external destination
- The same untrusted-input handling applies to content retrieved from
  [Memory](../harness/memory.md) — both are content the platform didn't
  directly author and shouldn't implicitly trust
- This component's injection-filtering principle is what
  `chat/fallback.py` implements in this project's own runtime (see
  `ARCHITECTURE.md` §4.1) — a concrete instance of the pattern described
  here, not just an abstract concern

## Sources

- [Trusted message history](https://strandsagents.com/docs/user-guide/safety-security/trusted-message-history/index.md) — checked 2026-08-12 — supports: message/content history should be built from a source the platform controls rather than an untrusted input, forged tool-result or instruction content in history can misrepresent what actually happened and steer the model's next step, and the explicit framing that the reliable control is a trust boundary rather than trying to sanitize untrusted content into being safe
