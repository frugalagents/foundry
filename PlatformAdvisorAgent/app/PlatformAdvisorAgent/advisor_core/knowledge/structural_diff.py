"""Structure-aware snapshot differences for decision-relevant changes."""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from html.parser import HTMLParser

from pydantic import Field

from .collection import CollectedDocument
from .models import FrozenModel, StrEnum, content_hash


class ChangeOperation(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class ChangeSignificance(StrEnum):
    INFORMATIONAL = "informational"
    DECISION_RELEVANT = "decision_relevant"


class StructuralBlock(FrozenModel):
    block_type: str = Field(min_length=1)
    text: str = Field(min_length=1)


class StructuralChange(FrozenModel):
    operation: ChangeOperation
    block_type: str = Field(min_length=1)
    before: str | None = None
    after: str | None = None
    significance: ChangeSignificance
    reason: str = Field(min_length=1)


class StructuralDiff(FrozenModel):
    source_id: str = Field(min_length=1)
    prior_snapshot_id: str = Field(min_length=1)
    current_snapshot_id: str = Field(min_length=1)
    prior_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    current_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prior_block_count: int = Field(ge=0)
    current_block_count: int = Field(ge=0)
    ignored_noise_blocks: int = Field(ge=0)
    changes: tuple[StructuralChange, ...]
    diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


IGNORED_HTML_TAGS = {
    "aside",
    "footer",
    "header",
    "nav",
    "noscript",
    "script",
    "style",
}
CAPTURE_TAGS = {
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "p": "paragraph",
    "li": "list",
    "th": "table",
    "td": "table",
    "pre": "code",
    "code": "code",
}
PRICE_PATTERN = re.compile(
    r"(?:[$\u00a3\u20ac\u00a5]\s?\d)|"
    r"\b(?:price|pricing|cost|per token|per request|per hour|per month)\b",
    re.IGNORECASE,
)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class _StructuralHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored_depth = 0
        self.ignored_noise_blocks = 0
        self.capture_stack: list[tuple[str, list[str]]] = []
        self.blocks: list[StructuralBlock] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in IGNORED_HTML_TAGS:
            self.ignored_depth += 1
            return
        if not self.ignored_depth and tag in CAPTURE_TAGS:
            self.capture_stack.append((CAPTURE_TAGS[tag], []))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in IGNORED_HTML_TAGS:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return
        if self.ignored_depth or tag not in CAPTURE_TAGS:
            return
        if not self.capture_stack:
            return
        block_type, parts = self.capture_stack.pop()
        text = _clean_text(" ".join(parts))
        if text:
            self.blocks.append(
                StructuralBlock(block_type=block_type, text=text)
            )

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return
        if self.ignored_depth:
            self.ignored_noise_blocks += 1
            return
        for _, parts in self.capture_stack:
            parts.append(text)


def _html_blocks(raw_body: bytes) -> tuple[tuple[StructuralBlock, ...], int]:
    parser = _StructuralHTMLParser()
    parser.feed(raw_body.decode("utf-8", errors="replace"))
    parser.close()
    return tuple(parser.blocks), parser.ignored_noise_blocks


def _json_blocks(raw_body: bytes) -> tuple[tuple[StructuralBlock, ...], int]:
    payload = json.loads(raw_body)
    blocks: list[StructuralBlock] = []

    def visit(value, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                visit(value[key], f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        else:
            block_type = (
                "schema"
                if any(
                    marker in path.lower()
                    for marker in (
                        "schema",
                        "properties",
                        "required",
                        "type",
                        "enum",
                    )
                )
                else "json"
            )
            blocks.append(
                StructuralBlock(
                    block_type=block_type,
                    text=(
                        f"{path}="
                        f"{json.dumps(value, sort_keys=True, ensure_ascii=True)}"
                    ),
                )
            )

    visit(payload, "")
    return tuple(blocks), 0


def structural_blocks(
    document: CollectedDocument,
) -> tuple[tuple[StructuralBlock, ...], int]:
    if document.media_type in {"text/html", "application/xhtml+xml"}:
        return _html_blocks(document.raw_body)
    if document.media_type in {
        "application/json",
        "application/schema+json",
    }:
        return _json_blocks(document.raw_body)
    return (
        tuple(
            StructuralBlock(block_type="text", text=line)
            for line in document.normalized_body.splitlines()
            if line.strip()
        ),
        0,
    )


def _significance(
    block_type: str,
    before: str | None,
    after: str | None,
) -> tuple[ChangeSignificance, str]:
    combined = " ".join(value for value in (before, after) if value)
    if block_type in {"table", "code", "schema"}:
        return (
            ChangeSignificance.DECISION_RELEVANT,
            f"{block_type} structure changed",
        )
    if PRICE_PATTERN.search(combined):
        return (
            ChangeSignificance.DECISION_RELEVANT,
            "pricing or cost language changed",
        )
    if block_type == "heading":
        return (
            ChangeSignificance.DECISION_RELEVANT,
            "document section structure changed",
        )
    return (
        ChangeSignificance.INFORMATIONAL,
        "descriptive content changed",
    )


def _change(
    operation: ChangeOperation,
    block_type: str,
    *,
    before: str | None = None,
    after: str | None = None,
) -> StructuralChange:
    significance, reason = _significance(block_type, before, after)
    return StructuralChange(
        operation=operation,
        block_type=block_type,
        before=before,
        after=after,
        significance=significance,
        reason=reason,
    )


def compare_snapshots(
    prior: CollectedDocument,
    current: CollectedDocument,
) -> StructuralDiff:
    """Compare two source snapshots while excluding known navigation noise."""

    if prior.source_id != current.source_id:
        raise ValueError("structural diff requires snapshots from one source")

    prior_blocks, prior_noise = structural_blocks(prior)
    current_blocks, current_noise = structural_blocks(current)
    prior_keys = [
        f"{block.block_type}:{block.text}" for block in prior_blocks
    ]
    current_keys = [
        f"{block.block_type}:{block.text}" for block in current_blocks
    ]
    matcher = SequenceMatcher(
        a=prior_keys,
        b=current_keys,
        autojunk=False,
    )
    changes: list[StructuralChange] = []
    for operation, prior_start, prior_end, current_start, current_end in (
        matcher.get_opcodes()
    ):
        if operation == "equal":
            continue
        removed = prior_blocks[prior_start:prior_end]
        added = current_blocks[current_start:current_end]
        paired = min(len(removed), len(added))
        for index in range(paired):
            before = removed[index]
            after = added[index]
            block_type = (
                before.block_type
                if before.block_type == after.block_type
                else f"{before.block_type}->{after.block_type}"
            )
            changes.append(
                _change(
                    ChangeOperation.MODIFIED,
                    block_type,
                    before=before.text,
                    after=after.text,
                )
            )
        for block in removed[paired:]:
            changes.append(
                _change(
                    ChangeOperation.REMOVED,
                    block.block_type,
                    before=block.text,
                )
            )
        for block in added[paired:]:
            changes.append(
                _change(
                    ChangeOperation.ADDED,
                    block.block_type,
                    after=block.text,
                )
            )

    payload = {
        "source_id": prior.source_id,
        "prior_snapshot_id": prior.snapshot_id,
        "current_snapshot_id": current.snapshot_id,
        "prior_content_hash": prior.normalized_content_hash,
        "current_content_hash": current.normalized_content_hash,
        "prior_block_count": len(prior_blocks),
        "current_block_count": len(current_blocks),
        "ignored_noise_blocks": prior_noise + current_noise,
        "changes": [change.model_dump(mode="json") for change in changes],
    }
    return StructuralDiff(
        **payload,
        diff_hash=content_hash(payload),
    )
