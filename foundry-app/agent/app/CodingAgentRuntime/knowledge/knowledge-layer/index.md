---
type: platform-component-group
title: Knowledge Layer
description: team-scoped codebase intelligence, org pattern mining, standards injection
group: knowledge-layer
tags: [knowledge-layer, rag, code-intelligence, org-knowledge]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [team-knowledge, codebase-context, knowledge-base, code-intelligence, org-patterns, standards-injection, entire-codebase-in-memory]
decision-question: "Do you need a persistent knowledge layer — indexed codebase retrieval, org pattern mining, or standards injection — beyond what fits in a session context window?"
---

The knowledge layer sits between raw codebase storage and the agent's in-session
context window. It provides durable, team-scoped knowledge that is retrieved
on demand rather than loaded wholesale into every session.

Three distinct concerns, each with its own governance model:

- [Code Intelligence](code-intelligence.md) — indexed RAG over a bounded codebase;
  fresh per commit; team-scoped; retrieval on demand
- [Org Knowledge](org-knowledge.md) — aggregate pattern mining across sessions;
  batch-extracted; governed by privacy/consent model
- [Standards Injection](standards-injection.md) — coding standards, architectural
  rules, compliance requirements delivered into every session

## When to activate this group

Signal from customer | Node to load
---|---
"We want the agent to know our entire codebase" | code-intelligence.md first — explain why RAG beats wholesale loading
"We want the agent to learn what the team does" | org-knowledge.md — distinguish from per-developer memory
"We want every agent to follow our coding standards" | standards-injection.md
"We have a Jira project and Bitbucket repo the team should always have context on" | code-intelligence.md + landscape.md
