---
type: platform-component
title: Code Intelligence
description: team-scoped indexed RAG over bounded codebase — retrieve, don't load
group: knowledge-layer
tags: [knowledge-layer, rag, code-intelligence, vector-store, codebase]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [codebase-context, entire-codebase-in-memory, code-rag, team-code-knowledge, bounded-repo]
decision-question: "How will the agent retrieve relevant code from your team's codebase without loading the entire repo into every session?"
---

Team-scoped indexed RAG over a bounded codebase: a vector store (or hybrid
vector + keyword store) re-indexed on each commit, queried at task start to
surface relevant files and symbols — without exhausting the context window.

## The "Entire Codebase in Memory" Question

Loading a large codebase wholesale into a 200K-token context window is rarely
correct:
- Cost: a 500K-line monorepo is ~40–80M tokens per session; even with prompt
  caching that is hundreds of dollars per developer per day
- Quality: dense code past ~50K tokens degrades model coherence; relevant
  signal is buried in noise
- Staleness: a loaded snapshot goes stale as the session progresses

The right answer is indexed RAG: fresh embeddings per commit, retrieved on
demand, scoped to what the task actually needs.

## Decisions

**Index scope?**
- Single repository — cleanest boundary; one team, one repo, one index
- Mono-repo with namespace isolation — index the whole monorepo; retrieve
  results scoped to the calling team's service namespace; namespace boundary
  is a security control, not just organisation
- Multi-repo — fan out indexes per team; cross-repo query requires federation

**Re-index frequency?**
- Per commit (webhook-triggered) — freshest; watch cost on very high-commit
  repos (many small commits to hot files)
- Scheduled (hourly or nightly) — simpler infra; acceptable staleness for
  most teams; choose if commit-triggered indexing costs are too high

**Retrieval strategy?**
- Dense vector only — semantic similarity queries ("code that handles payments")
- Hybrid (vector + BM25 keyword) — better for exact symbol lookups ("find
  all callers of AuthService.validateToken") alongside semantic queries
- Re-rank on top-K — small re-ranker model improves precision; adds latency
  and cost; worth it for high-precision use cases

**Where does the index live?**
- Bedrock Knowledge Bases — managed vector store with native Bedrock retrieval
  and IAM-based access control; natural fit for AgentCore stacks
- Self-managed (pgvector, OpenSearch Serverless) — more control, more ops burden

## Stack Options

**Managed vector store (AWS)**
- Amazon Bedrock Knowledge Bases — fully managed; supports hybrid search
  (vector + BM25); IAM-based access control; native retrieval API callable from
  Bedrock models and AgentCore; re-index via S3 data source sync job; fits
  AgentCore-based stacks without additional infra

**Self-managed vector store (OS)**
- pgvector (PostgreSQL extension) — lowest operational overhead if you already
  run RDS/Aurora; hybrid search with pg_search; suitable for single-repo indexes
  of moderate size
- OpenSearch Serverless — AWS-managed OpenSearch; vector + keyword search; scales
  to large codebases; more complex than pgvector but stronger at large-scale
  BM25 hybrid search
- Chroma / Qdrant / Weaviate — lightweight self-hosted vector stores; good for
  local or containerised deployment; require you to manage persistence and scaling

**Embedding models**
- Amazon Titan Embeddings (Bedrock) — managed; no infrastructure; invoked per
  commit via Bedrock API; good default for Bedrock Knowledge Bases ingestion
- Cohere Embed v3 (Bedrock) — strong code-specific embedding quality; also
  managed via Bedrock API
- `sentence-transformers` (OS) — self-hosted; run in a Lambda or ECS task
  on commit webhook; full control over model and batching

**Re-index pipeline**
- AWS CodePipeline / EventBridge Pipes — trigger on CodeCommit/GitHub webhook;
  invoke an embedding Lambda; upsert vectors to the knowledge base
- GitHub Actions + Lambda — simpler for GitHub-hosted repos; Action triggers
  on push, calls an embedding API, updates the vector store

**Retrieval (query time)**
- Bedrock Knowledge Bases Retrieve API — single call, returns ranked chunks
  with source attribution; supports metadata filtering for namespace isolation
- LlamaIndex RetrievalQA (OS) — query layer over any vector store; supports
  re-ranking, query expansion, and hybrid search pipeline configuration

## Principles

- Retrieve, don't load — always prefer retrieval over wholesale context injection
  for anything larger than a handful of files
- Namespace isolation is a security boundary: team A must not retrieve team B's
  code through a shared index; enforce at query time, not just at write time
- Freshness directly affects quality — stale embeddings produce missed symbols
  and outdated pattern suggestions; design re-indexing as a first-class pipeline
  step, not an afterthought
- The code intelligence index complements session context, not replaces it:
  retrieved chunks populate the window for the current task; the window still
  manages that budget

## Connects to

- [Context](../harness/context.md) — retrieved chunks consume the session context
  window; the two must be sized together to avoid overflow
- [Standards Injection](standards-injection.md) — standards are a separate index;
  don't conflate code retrieval with standards delivery
- [Org Knowledge](org-knowledge.md) — code intelligence indexes what exists;
  org knowledge mines what patterns emerge across sessions
- [Observability & Audit](../ops/observability.md) — log every retrieval query
  and result set for quality debugging and namespace-isolation auditing

## Sources

- [Amazon Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) — checked 2026-08-12 — managed vector store, native retrieval, IAM access control, hybrid search support
