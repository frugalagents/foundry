"""Loads the OKF knowledge graph from the markdown files in knowledge/.

The knowledge/ directory mirrors the `Coding Agent Advisor/knowledge/` folder.
Each .md file is an OKF node. The loader derives routing metadata from the
node frontmatter and markdown links instead of maintaining a hardcoded Python
copy of the graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Iterable

import yaml


_EDGE_FIELDS = (
    "alternatives",
    "implies",
    "conflicts_with",
    "requires",
    "exception_to",
)


@dataclass(frozen=True)
class KnowledgeNode:
    path: str
    title: str
    content: str = ""
    description: str = ""
    group: str = ""
    status: str = ""
    tags: tuple[str, ...] = ()
    traversal: str = ""
    triggers: tuple[str, ...] = ()
    trigger_pool: tuple[str, ...] = ()
    trigger_pool_min_matches: int = 0
    decision_question: str = ""
    decision_domain: str = ""
    priority: int = 0
    blocking: bool = False
    linked_paths: tuple[str, ...] = field(default_factory=tuple)
    alternatives: tuple[str, ...] = field(default_factory=tuple)
    implies: tuple[str, ...] = field(default_factory=tuple)
    conflicts_with: tuple[str, ...] = field(default_factory=tuple)
    requires: tuple[str, ...] = field(default_factory=tuple)
    exception_to: tuple[str, ...] = field(default_factory=tuple)
    fit_signals: tuple[str, ...] = ()
    retire_signals: tuple[str, ...] = ()
    source_file: str = ""
    search_text: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def typed_edges(self) -> dict[str, tuple[str, ...]]:
        return {
            "alternatives": self.alternatives,
            "implies": self.implies,
            "conflicts_with": self.conflicts_with,
            "requires": self.requires,
            "exception_to": self.exception_to,
        }

    @property
    def edge_paths(self) -> tuple[str, ...]:
        ordered: list[str] = []
        for field_name in _EDGE_FIELDS:
            ordered.extend(getattr(self, field_name))
        ordered.extend(self.linked_paths)
        return tuple(dict.fromkeys(ordered))


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._body_cache: dict[str, str] = {}
        self._load(knowledge_dir)

    def _load(self, knowledge_dir: Path) -> None:
        if not knowledge_dir.exists():
            return
        for md_file in knowledge_dir.rglob("*.md"):
            rel = md_file.relative_to(knowledge_dir)
            path = str(rel.with_suffix(""))
            raw = md_file.read_text(encoding="utf-8", errors="replace")
            frontmatter, body = _split_frontmatter(raw)
            title = str(frontmatter.get("title") or _extract_title(body) or path)
            traversal = str(frontmatter.get("traversal") or "").strip().lower()
            trigger_pool_min_matches = _as_int(frontmatter.get("trigger_pool_min_matches"))
            description = str(frontmatter.get("description") or "").strip()
            tags = tuple(_normalize_list(frontmatter.get("tags")))
            decision_question = str(frontmatter.get("decision_question") or "").strip()
            self._nodes[path] = KnowledgeNode(
                path=path,
                title=title,
                content="",
                description=description,
                group=str(frontmatter.get("group") or "").strip(),
                status=str(frontmatter.get("status") or "").strip(),
                tags=tags,
                traversal=traversal,
                triggers=tuple(_normalize_list(frontmatter.get("trigger"))),
                trigger_pool=tuple(_normalize_list(frontmatter.get("trigger_pool"))),
                trigger_pool_min_matches=trigger_pool_min_matches,
                decision_question=decision_question,
                decision_domain=str(frontmatter.get("decision_domain") or frontmatter.get("group") or "").strip(),
                priority=_as_int(frontmatter.get("priority")),
                blocking=_as_bool(frontmatter.get("blocking")),
                linked_paths=tuple(_extract_linked_paths(path, body)),
                alternatives=tuple(_normalize_path_list(path, frontmatter.get("alternatives"))),
                implies=tuple(_normalize_path_list(path, frontmatter.get("implies"))),
                conflicts_with=tuple(_normalize_path_list(path, frontmatter.get("conflicts_with"))),
                requires=tuple(_normalize_path_list(path, frontmatter.get("requires"))),
                exception_to=tuple(_normalize_path_list(path, frontmatter.get("exception_to"))),
                fit_signals=tuple(_normalize_list(frontmatter.get("fit_signals"))),
                retire_signals=tuple(_normalize_list(frontmatter.get("retire_signals"))),
                source_file=str(md_file),
                search_text=_build_search_text(path, title, description, tags, decision_question, body),
                metadata=frontmatter,
            )

    def get(self, path: str, *, include_content: bool = False) -> KnowledgeNode | None:
        node = self._nodes.get(path)
        if node is None:
            return None
        return self.materialize_node(node) if include_content else node

    def get_content(self, path_or_node: str | KnowledgeNode) -> str:
        if isinstance(path_or_node, KnowledgeNode):
            if path_or_node.content:
                return path_or_node.content
            path = path_or_node.path
        else:
            path = path_or_node

        if path in self._body_cache:
            return self._body_cache[path]

        node = self._nodes.get(path)
        if node is None:
            return ""
        if node.content:
            self._body_cache[path] = node.content
            return node.content
        if not node.source_file:
            return ""

        raw = Path(node.source_file).read_text(encoding="utf-8", errors="replace")
        _, body = _split_frontmatter(raw)
        self._body_cache[path] = body
        return body

    def materialize_node(self, path_or_node: str | KnowledgeNode) -> KnowledgeNode | None:
        node = path_or_node if isinstance(path_or_node, KnowledgeNode) else self._nodes.get(path_or_node)
        if node is None:
            return None
        if node.content:
            return node
        content = self.get_content(node.path)
        return replace(node, content=content)

    def materialize_nodes(self, nodes: Iterable[KnowledgeNode]) -> list[KnowledgeNode]:
        materialized: list[KnowledgeNode] = []
        for node in nodes:
            hydrated = self.materialize_node(node)
            if hydrated is not None:
                materialized.append(hydrated)
        return materialized

    def mandate_nodes(self) -> list[KnowledgeNode]:
        return sorted(
            [n for n in self._nodes.values() if n.traversal == "mandate"],
            key=lambda n: n.path,
        )

    def query(self, keywords: str, max_results: int = 4) -> list[KnowledgeNode]:
        """Search across all nodes using metadata + compact searchable text."""
        terms = [t.lower().strip() for t in re.split(r"[,\s]+", keywords) if t.strip()]
        if not terms:
            return self.mandate_nodes()[:max_results]

        scored: list[tuple[float, KnowledgeNode]] = []
        for node in self._nodes.values():
            combined = node.search_text.lower() if node.search_text else " ".join(
                (
                    node.path.lower(),
                    node.title.lower(),
                    node.description.lower(),
                    " ".join(node.tags),
                    node.decision_question.lower(),
                )
            )

            score = 0.0
            matched_text = False
            for t in terms:
                if t in combined:
                    score += 1.0
                    matched_text = True
                if re.search(r"\b" + re.escape(t) + r"\b", combined):
                    score += 1.0
                    matched_text = True
                if t in node.title.lower():
                    score += 1.5
                    matched_text = True
                if t in node.description.lower():
                    score += 0.75
                    matched_text = True
                if t in " ".join(node.tags):
                    score += 0.75
                    matched_text = True
                if t in node.path:
                    score += 2.0
                    matched_text = True
                path_segments = [segment for segment in node.path.split("/") if segment]
                if t in path_segments:
                    score += 2.5
                    matched_text = True
                if node.path == t or node.path.endswith(f"/{t}"):
                    score += 2.5
                    matched_text = True
            if len(terms) > 1 and " ".join(terms) in combined:
                score += 3.0
                matched_text = True
            if not matched_text:
                continue
            if node.blocking:
                score += 0.2
            score += min(len(node.edge_paths), 5) * 0.1

            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: (-x[0], x[1].path))
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
        """Return follow-on nodes for a set of loaded nodes.

        Typed edges are preferred; generic markdown links are fallback adjacency.
        """
        seen = set(node_paths)
        related: list[KnowledgeNode] = []
        for node_path in node_paths:
            node = self._nodes.get(node_path)
            if not node:
                continue
            for linked_path in node.edge_paths:
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


def _build_search_text(
    path: str,
    title: str,
    description: str,
    tags: tuple[str, ...],
    decision_question: str,
    body: str,
) -> str:
    compact_body = body.strip()
    sources_index = compact_body.find("\n## Sources")
    if sources_index >= 0:
        compact_body = compact_body[:sources_index].rstrip()
    compact_body = re.sub(r"\s+", " ", compact_body)
    compact_body = compact_body[:2200]
    return " ".join(
        part for part in (
            path,
            title,
            description,
            " ".join(tags),
            decision_question,
            compact_body,
        ) if part
    )


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
    loaded = yaml.safe_load(block) or {}
    if not isinstance(loaded, dict):
        return {}
    return _normalize_frontmatter_mapping(loaded)


def _parse_frontmatter_value(value: str) -> object:
    if not value:
        return ""
    if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
        try:
            return _normalize_frontmatter_mapping(yaml.safe_load(value)) if value.startswith("{") else _normalize_frontmatter_sequence(yaml.safe_load(value))
        except Exception:
            pass
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
    value = _strip_quotes(value)
    if value.isdigit():
        return int(value)
    if value.lower() in {"true", "false", "yes", "no"}:
        return value.lower() in {"true", "yes"}
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


def _normalize_frontmatter_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, object] = {}
    for key, item in value.items():
        normalized[str(key).strip().replace("-", "_")] = _normalize_frontmatter_node(item)
    return normalized


def _normalize_frontmatter_sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return [_normalize_frontmatter_node(item) for item in value]


def _normalize_frontmatter_node(value: object) -> object:
    if isinstance(value, dict):
        return _normalize_frontmatter_mapping(value)
    if isinstance(value, list):
        return _normalize_frontmatter_sequence(value)
    return value


def _normalize_path_list(node_path: str, value: object) -> list[str]:
    raw_items: list[str]
    if isinstance(value, list):
        raw_items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        raw_items = [value.strip()]
    else:
        return []

    resolved: list[str] = []
    for item in raw_items:
        normalized = _normalize_frontmatter_path(node_path, item)
        if normalized:
            resolved.append(normalized)
    return list(dict.fromkeys(resolved))


def _normalize_frontmatter_path(node_path: str, raw_path: str) -> str | None:
    value = raw_path.split("#", 1)[0].strip()
    if not value or "://" in value:
        return None
    if value.endswith(".md"):
        return _resolve_link(node_path, value)

    if value.startswith("./") or value.startswith("../"):
        base = PurePosixPath(node_path).parent
        normalized = posixpath.normpath(str(base / value))
    else:
        normalized = posixpath.normpath(value)
    return normalized if normalized and normalized != "." else None


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return False


def _matches_any_trigger(triggers: tuple[str, ...], text_lower: str) -> bool:
    return any(trigger in text_lower for trigger in triggers)


def _count_trigger_matches(triggers: tuple[str, ...], text_lower: str) -> int:
    spans: list[tuple[int, int]] = []
    match_count = 0
    for trigger in sorted(set(triggers), key=len, reverse=True):
        for match in re.finditer(re.escape(trigger), text_lower):
            span = match.span()
            if any(not (span[1] <= other[0] or span[0] >= other[1]) for other in spans):
                continue
            spans.append(span)
            match_count += 1
            break
    return match_count


def _extract_linked_paths(node_path: str, body: str) -> list[str]:
    linked_paths: list[str] = []
    for section in ("Sub-nodes", "Connects to"):
        linked_paths.extend(_extract_section_links(node_path, body, section))
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
