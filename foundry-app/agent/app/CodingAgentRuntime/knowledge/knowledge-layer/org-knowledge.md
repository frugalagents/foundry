---
type: platform-component
title: Org Knowledge Extraction
description: aggregate team pattern mining across sessions — discover what teams do
group: knowledge-layer
tags: [knowledge-layer, org-knowledge, pattern-mining, memory-extraction, team-patterns]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [team-knowledge, org-patterns, learn-from-sessions, common-practices, knowledge-mining]
decision-question: "Do you want the platform to mine cross-session patterns to discover what the team is converging on, and surface that as platform-level knowledge?"
---

Org knowledge extraction mines aggregate patterns from the platform's session
history — identifying solutions teams are converging on, which approaches are
being reinvented repeatedly, and where platform-level guidance would save effort.
It is the team-level complement to per-developer [Memory](../harness/memory.md).

## What It Is

Batch-extracted structured knowledge from anonymized or consented session data:
common refactoring patterns, repeated error/fix pairs, frequently adopted
architectural decisions, library preferences observed across many tasks.

The output is actionable intelligence for the platform team (to improve defaults
and policies) and optionally for developers (surfaced as in-session guidance).

## What It Is Not

- Not real-time — extraction runs in batch (daily or weekly); patterns evolve
  slowly enough that this is acceptable
- Not individual developer surveillance — data must be anonymized or explicitly
  consented before aggregation; this is a data governance decision, not a
  technical one
- Not a substitute for explicit standards — org knowledge discovers what teams
  do; [Standards Injection](standards-injection.md) encodes what they should do

## Decisions

**Data governance model — resolve this first**
- Anonymized aggregate — no session traceable to an individual; safer, lower
  signal on some pattern types
- Consented identifiable — developers opt in to contributing attributable
  sessions; higher signal; requires explicit privacy policy and consent flow
- Enterprise data classification governs which repos' sessions may be aggregated
  at all; confirm before building any pipeline

**Extraction mechanism?**
- Bedrock AgentCore Memory extraction jobs — native; runs over stored events,
  produces structured knowledge records; requires AgentCore Memory adoption
- Custom pipeline — export session logs to a data warehouse, run NLP/embedding
  extraction offline; more flexibility, more build effort

**Who consumes extracted knowledge?**
- Platform team only — improves defaults, recommended patterns, policy tuning;
  no developer-facing exposure
- Developer-facing — surfaced as contextual guidance in IDE or agent context;
  higher value, requires quality bar before surfacing

## Stack Options

**Extraction (AWS managed)**
- Amazon Bedrock AgentCore Memory — stores session events natively; runs
  extraction jobs over stored events to produce structured knowledge records
  (entities, relations, patterns); no custom pipeline needed if already on
  AgentCore; job results written to the Memory store and queryable by agents

**Extraction (custom pipeline on AWS)**
- Amazon Kinesis Data Firehose + S3 — stream session logs from the harness to
  S3 in near-real-time; trigger a Glue job or Lambda for periodic extraction
- AWS Glue — ETL over S3 session archives; run NLP extraction (entity
  recognition, pattern classification) using a Bedrock model call per batch;
  write structured outputs to DynamoDB or Aurora
- Amazon Comprehend — managed NLP for entity recognition and PII detection in
  session text; useful for anonymizing before extraction or for identifying
  code-specific patterns in session transcripts

**Extraction (open source)**
- Apache Airflow (MWAA on AWS) — orchestrate extraction DAGs on schedule;
  call Bedrock for embeddings and pattern summarization; write to any store
- LLM-based extraction — use a Bedrock model (Haiku-class for cost efficiency)
  to summarize batches of sessions and extract structured patterns; prompt-
  engineering the extraction is cheaper than building a custom NLP pipeline
  for most team sizes

**Storage and query**
- AgentCore Memory store — native for AgentCore stacks; queryable by agents
  at session start to surface relevant team-level context
- Amazon DynamoDB — simple structured record store for extracted patterns;
  low operational overhead; good for team-scoped key-value pattern retrieval
- Amazon OpenSearch — if patterns need full-text or semantic search at query
  time (e.g., "has the team solved this kind of problem before?")

## Principles

- Data governance is the first decision, not a detail — build the consent and
  anonymization model before designing any extraction pipeline
- Extraction should produce specific, actionable output (concrete patterns, not
  vague summaries) or the investment won't be used
- Distinguish discovery (what teams do, from extraction) from prescription
  (what they should do, from standards) — conflating them causes policy drift
  where observed bad practices become implied standards

## Connects to

- [Memory](../harness/memory.md) — org knowledge is the team-level tier of the
  memory hierarchy; individual developer memory sits below it; neither replaces
  the other
- [Standards Injection](standards-injection.md) — extraction results are candidates
  for promotion into formal standards; the review gate between them matters
- [Observability & Audit](../ops/observability.md) — session data used for
  extraction must be governed under the same audit policy as other agent logs;
  extraction is not a side channel around data retention commitments

## Sources

- [AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html) — to verify on first use — extraction jobs over stored session events, structured record output
