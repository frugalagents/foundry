---
type: platform-component
title: Enterprise Landscape
description: Jira · GitHub · APIs · DBs
group: external
tags: [external, integrations]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

The systems of record the agent acts on, reached through the
[MCP Gateway](../gateway/mcpgw.md) — source control, issue trackers, wikis,
internal services and databases. This component is the set of *destinations*
the gateway brokers access to; the gateway itself is what enforces policy on
every call into them.

## Decisions

**Integration surface priority?**
- SCM + tracker first (GitHub/GitLab + Jira) — the two systems almost every
  coding-agent workflow touches immediately
- + internal APIs as MCP servers — extends reach to proprietary systems
  once the core SCM/tracker integration is working
- + data stores — read-only vs. read-write is a meaningfully different risk
  tier here specifically, since a database write has a different blast
  radius than a database read in a way that's less true for, say, an issue
  tracker comment

**Credential model per system?**
- Shared service account across all integrations — simplest, but a single
  compromised credential reaches everything
- Least-privilege service account per system — more setup, contains a
  compromise to one system

## Principles

- Prefer official APIs and webhooks over scraping or unofficial endpoints —
  official interfaces are the ones vendors actually support and version
- Least-privilege service accounts per system, not one shared credential
  across every integration — ties directly to
  [Provenance](../registry/provenance.md)'s per-artifact vetting and
  [Identity & Access](../access/identity.md)'s scoped-identity principle
- Read and write access to a given system are different risk tiers and
  should be independently grantable, same principle as
  [Tools & Plugins](../registry/tools.md)'s read/write separation

## Connects to

- Reached exclusively through the [MCP Gateway](../gateway/mcpgw.md) — never
  a direct connection from the harness
- Each integration is itself registered as an [MCP Server](../registry/mcpservers.md)
  and vetted per [Provenance](../registry/provenance.md) before being trusted

## Sources

- Verify against current docs — this file describes the general
  enterprise-integration pattern (official APIs, least-privilege service
  accounts, read/write risk-tiering) as stated in the original architecture
  diagram, not a citation-backed claim about a specific product's
  integration catalog. Corroborate with a concrete source before treating
  any claim here as settled fact.
