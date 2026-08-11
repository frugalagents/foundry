from __future__ import annotations

from pathlib import Path

import pytest

from advisor_core.knowledge import OkfLoadError, load_okf_corpus


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CAPABILITY_DIRECTORY = REPOSITORY_ROOT / "knowledge" / "capabilities"


def test_loads_repository_capability_pages_deterministically():
    first = load_okf_corpus(CAPABILITY_DIRECTORY)
    second = load_okf_corpus(CAPABILITY_DIRECTORY)

    assert [document.record.id for document in first.documents] == [
        "capability:isolated-execution",
        "capability:model-routing",
        "capability:governed-tool-access",
    ]
    assert [document.document_hash for document in first.documents] == [
        document.document_hash for document in second.documents
    ]
    assert first.relationships == ()
    assert len(first.entities) == 3


def test_rejects_markdown_without_front_matter(tmp_path: Path):
    path = tmp_path / "invalid.md"
    path.write_text("# Missing metadata\n", encoding="utf-8")

    with pytest.raises(OkfLoadError, match="must begin with YAML front matter"):
        load_okf_corpus(path)


def test_rejects_duplicate_record_ids(tmp_path: Path):
    content = """---
schema_version: "1.0"
kind: Capability
id: capability:duplicate
title: Duplicate
summary: Duplicate semantic record.
lifecycle: draft
owner_id: team:platform-advisor
effective_from: 2026-08-11
stale_after: 2027-02-11
category: test
---
# Duplicate
"""
    (tmp_path / "first.md").write_text(content, encoding="utf-8")
    (tmp_path / "second.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="record IDs must be unique"):
        load_okf_corpus(tmp_path)
