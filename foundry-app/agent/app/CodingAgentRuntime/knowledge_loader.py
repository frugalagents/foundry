"""Loads the OKF knowledge graph from the markdown files in knowledge/.

The knowledge/ directory mirrors the `Coding Agent Advisor/knowledge/` folder.
Each .md file is an OKF node. The loader now derives routing metadata from the
node frontmatter and markdown links instead of maintaining a hardcoded Python
copy of the graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import posixpath
import re
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class KnowledgeNode:
    path: str
    title: str
    content: str
    traversal: str = ""
    triggers: tuple[str, ...] = ()
    trigger_pool: tuple[str, ...] = ()
    trigger_pool_min_matches: int = 0
    decision_question: str = ""
    linked_paths: tuple[str, ...] = field(default_factory=tuple)


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
            raw = md_file.read_text(encoding="utf-8", errors="replace")
            frontmatter, body = _split_frontmatter(raw)
            title = str(frontmatter.get("title") or _extract_title(body) or path)
            traversal = str(frontmatter.get("traversal") or "").strip().lower()
            trigger_pool_min_matches = _as_int(frontmatter.get("trigger_pool_min_matches"))
            self._nodes[path] = KnowledgeNode(
                path=path,
                title=title,
                content=body,
                traversal=traversal,
                triggers=tuple(_normalize_list(frontmatter.get("trigger"))),
                trigger_pool=tuple(_normalize_list(frontmatter.get("trigger_pool"))),
                trigger_pool_min_matches=trigger_pool_min_matches,
                decision_question=str(frontmatter.get("decision_question") or "").strip(),
                linked_paths=tuple(_extract_linked_paths(path, body)),
            )

    def get(self, path: str) -> KnowledgeNode | None:
        return self._nodes.get(path)

    def mandate_nodes(self) -> list[KnowledgeNode]:
        return sorted(
            [n for n in self._nodes.values() if n.traversal == "mandate"],
            key=lambda n: n.path,
        )

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
        triggered: list[KnowledgeNode] = []
        for node in self._nodes.values():
            if node.traversal != "conditional":
                continue
            if _matches_any_trigger(node.triggers, text_lower):
                triggered.append(node)
                continue
            if (
                node.trigger_pool
                and node.trigger_pool_min_matches > 0
                and _count_trigger_matches(node.trigger_pool, text_lower) >= node.trigger_pool_min_matches
            ):
                triggered.append(node)
        return sorted(triggered, key=lambda n: n.path)

    def related_nodes_for(self, node_paths: list[str], *, max_results: int = 6) -> list[KnowledgeNode]:
        """Return directly linked follow-on nodes for a set of loaded nodes."""
        seen = set(node_paths)
        related: list[KnowledgeNode] = []
        for node_path in node_paths:
            node = self._nodes.get(node_path)
            if not node:
                continue
            for linked_path in node.linked_paths:
                if linked_path in seen:
                    continue
                linked = self._nodes.get(linked_path)
                if not linked:
                    continue
                related.append(linked)
                seen.add(linked_path)
                if len(related) >= max_results:
                    return related
        return related


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, flags=re.DOTALL)
    if not match:
        return {}, text
    return _parse_frontmatter(match.group(1)), text[match.end():]


def _parse_frontmatter(block: str) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().replace("-", "_")] = _parse_frontmatter_value(value.strip())
    return metadata


def _parse_frontmatter_value(value: str) -> object:
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
    value = _strip_quotes(value)
    if value.isdigit():
        return int(value)
    return value


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _normalize_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().lower()]
    return []


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _matches_any_trigger(triggers: tuple[str, ...], text_lower: str) -> bool:
    return any(trigger in text_lower for trigger in triggers)


def _count_trigger_matches(triggers: tuple[str, ...], text_lower: str) -> int:
    return sum(1 for trigger in triggers if trigger in text_lower)


def _extract_linked_paths(node_path: str, body: str) -> list[str]:
    linked_paths: list[str] = []
    for section in ("Sub-nodes", "Connects to"):
        linked_paths.extend(_extract_section_links(node_path, body, section))
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(linked_paths))


def _extract_section_links(node_path: str, body: str, section_name: str) -> list[str]:
    pattern = rf"^## {re.escape(section_name)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE)
    if not match:
        return []
    section_body = match.group(1)
    return [
        resolved
        for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", section_body)
        if (resolved := _resolve_link(node_path, href))
    ]


def _resolve_link(node_path: str, href: str) -> str | None:
    href = href.split("#", 1)[0].strip()
    if not href or "://" in href or not href.endswith(".md"):
        return None
    base = PurePosixPath(node_path).parent
    raw_path = str(base / href)
    normalized = posixpath.normpath(raw_path)
    if normalized == ".":
        return None
    return normalized[:-3] if normalized.endswith(".md") else normalized


def load_knowledge_base(knowledge_dir: Path) -> KnowledgeBase:
    return KnowledgeBase(knowledge_dir)
