"""Loads the OKF knowledge graph from the markdown files in knowledge/.

The knowledge/ directory mirrors the `Coding Agent Advisor/knowledge/` folder.
Each .md file is an OKF node. The loader indexes them by their relative path
(e.g. "harness-selection/index", "access/identity") and builds a simple
keyword-search index for the query_knowledge tool.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import NamedTuple

# Nodes that must be loaded for every customer regardless of signals.
MANDATE_NODES = {
    "surfaces/ide",
    "access/identity",
    "access/guardrails",
    "access/quota",
    "external/providers",
    "ops/observability",
    "exec/local",
    "access/security-posture",
    "harness-selection/index",
    "harness-selection/lifecycle-implications",
    "harness-selection/saas-products",
}

# Keyword → conditional node mappings (from coding-agent-advisor.md)
CONDITIONAL_NODES: list[tuple[list[str], str]] = [
    (["multi-provider", "model routing", "cost tier"],      "gateway/model-tiering"),
    (["model routing", "model gateway", "tiering"],          "gateway/modelgw"),
    (["mcp", "mcp gateway", "tool routing"],                 "gateway/mcpgw"),
    (["chat surface", "pr bot", "scm"],                      "surfaces/chat"),
    (["cli", "terminal", "scripted agent"],                  "surfaces/cli"),
    (["ci/cd", "pipeline", "autonomous"],                    "surfaces/ci"),
    (["jupyter", "notebook", "data science"],                "surfaces/jupyterlab"),
    (["custom agent", "managed runtime", "agentcore"],       "harness-selection/managed-runtime"),
    (["oss", "strands", "langchain", "full control"],        "harness-selection/oss-frameworks"),
    (["opencode", "pi agent", "cline", "goose", "aider",
      "codex cli", "swe-agent", "mastra", "deep agents",
      "hermes agent", "openhands", "pre-built harness",
      "coding harness", "open source harness"],             "harness-selection/coding-harnesses"),
    (["memory", "cross-session", "personalization"],         "harness/memory"),
    (["context", "context window"],                          "harness/context"),
    (["loop", "agentic loop", "multi-turn"],                 "harness/loop"),
    (["permission", "approval", "human-in-loop"],            "harness/perms"),
    (["rollback", "undo", "revert"],                         "harness/rollback"),
    (["container", "ephemeral", "sandbox"],                  "exec/container"),
    (["microvm", "firecracker", "strong isolation"],         "exec/microvm"),
    (["remote execution", "centralized infra"],              "exec/remote"),
    (["on-premises", "air-gapped", "hil", "hardware"],       "exec/on-prem-runner"),
    (["gcp", "google cloud", "gcp runner"],                  "exec/gcp-runner"),
    (["code intelligence", "codebase rag", "indexing"],      "knowledge-layer/code-intelligence"),
    (["org knowledge", "team knowledge", "patterns"],        "knowledge-layer/org-knowledge"),
    (["standards", "claude.md", "system prompt injection"],  "knowledge-layer/standards-injection"),
    (["cost", "chargeback", "finops"],                       "ops/cost"),
    (["session economics", "per-session", "ceiling"],        "ops/session-economics"),
    (["token", "token cost", "token budget"],                "ops/token"),
    (["resilience", "circuit-breaker", "retry", "ha"],       "ops/resilience"),
    (["multi-cloud", "azure", "gcp workloads"],              "ops/multi-cloud-governance"),
    (["federation", "multi-instance", "business unit"],      "ops/federation"),
    (["policy tier", "innovation lab", "restricted"],        "access/policy-tiers"),
    (["itar", "ear", "export control", "defense"],           "access/export-control"),
    (["legal hold", "e-discovery", "worm"],                  "access/legal-hold"),
    (["multiple idp", "idp federation", "acquisition"],      "access/idp-federation"),
    (["gdpr", "works council", "eu monitoring"],             "access/regional-compliance"),
    (["china", "data residency", "pipl"],                    "access/data-jurisdiction"),
    (["hipaa", "phi", "healthcare"],                         "access/hipaa"),
    (["sox", "financial reporting", "audit trail"],          "access/sox"),
    (["mnpi", "insider trading", "material non-public"],     "access/mnpi"),
    (["cmmc", "dod", "itar", "defense contractor"],          "access/cmmc"),
    (["model risk", "mrm", "banking", "model validation"],   "access/model-risk-management"),
    (["progressive trust", "trust model"],                   "access/progressive-trust"),
    (["cyberark", "vault", "pam", "privileged access"],      "gateway/cyberark-integration"),
    (["vault integration", "hashicorp"],                     "gateway/vault-integration"),
    (["code eval", "evals", "quality"],                      "quality/evals"),
    (["capability eval", "model benchmark"],                 "quality/model-capability-eval"),
    (["safety critical", "safety eval"],                     "quality/safety-critical-eval"),
    (["external provider", "web browsing", "search"],        "external/web"),
    (["landscape", "competitive", "providers"],              "external/landscape"),
    (["registry", "tool registry", "mcp server"],            "registry/index"),
    (["mcp server", "mcp registry"],                         "registry/mcpservers"),
    (["skills", "skill", "skill registry"],                  "registry/skills"),
    (["subagent", "sub-agent"],                              "registry/subagents"),
    (["tool", "tools", "function calling"],                  "registry/tools"),
    (["provenance", "supply chain", "artifact"],             "registry/provenance"),
    (["enterprise cost", "cost model", "enterprise spend"],  "ops/cost-model-enterprise"),
    (["security ops", "siem", "incident"],                   "access/security-ops"),
]


class KnowledgeNode(NamedTuple):
    path: str        # e.g. "access/identity"
    title: str       # first H1 heading or filename
    content: str     # full markdown text


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._load(knowledge_dir)

    def _load(self, knowledge_dir: Path) -> None:
        if not knowledge_dir.exists():
            return
        for md_file in knowledge_dir.rglob("*.md"):
            rel = md_file.relative_to(knowledge_dir)
            path = str(rel.with_suffix(""))  # "access/identity"
            text = md_file.read_text(encoding="utf-8", errors="replace")
            title = _extract_title(text) or path
            self._nodes[path] = KnowledgeNode(path=path, title=title, content=text)

    def get(self, path: str) -> KnowledgeNode | None:
        return self._nodes.get(path)

    def mandate_nodes(self) -> list[KnowledgeNode]:
        return [n for p, n in self._nodes.items() if p in MANDATE_NODES]

    def query(self, keywords: str, max_results: int = 4) -> list[KnowledgeNode]:
        """Search across all nodes using multi-signal scoring."""
        terms = [t.lower().strip() for t in re.split(r"[,\s]+", keywords) if t.strip()]
        if not terms:
            return self.mandate_nodes()[:max_results]

        scored: list[tuple[float, KnowledgeNode]] = []
        for node in self._nodes.values():
            body = node.content.lower()
            title = node.title.lower()
            combined = title + " " + body

            score = 0.0
            for t in terms:
                if t in combined:
                    score += 1.0                                    # substring hit
                if re.search(r"\b" + re.escape(t) + r"\b", combined):
                    score += 1.0                                    # whole-word bonus
                if t in title:
                    score += 1.5                                    # title hit bonus
            # Phrase bonus — all terms appear contiguously
            if len(terms) > 1 and " ".join(terms) in combined:
                score += 3.0
            # Path match bonus
            if any(t in node.path for t in terms):
                score += 2.0

            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: -x[0])
        return [n for _, n in scored[:max_results]]

    def conditional_nodes_for(self, conversation_text: str) -> list[KnowledgeNode]:
        """Return conditional nodes triggered by signals in the conversation."""
        text_lower = conversation_text.lower()
        triggered: set[str] = set()
        for keywords, node_path in CONDITIONAL_NODES:
            if any(kw in text_lower for kw in keywords):
                triggered.add(node_path)
        return [n for p in triggered if (n := self._nodes.get(p)) is not None]


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def load_knowledge_base(knowledge_dir: Path) -> KnowledgeBase:
    return KnowledgeBase(knowledge_dir)
