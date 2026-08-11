from __future__ import annotations

from pathlib import Path

import yaml

from advisor_core.knowledge import Capability


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CAPABILITY_DIRECTORY = REPOSITORY_ROOT / "knowledge" / "capabilities"
REQUIRED_SECTIONS = (
    "## Purpose",
    "## Architecture Role",
    "## Relationship Intent",
    "## Decision Guidance",
    "## Evidence State",
)


def read_front_matter(path: Path) -> tuple[dict[str, object], str]:
    document = path.read_text(encoding="utf-8")
    opening, metadata, body = document.split("---", maxsplit=2)
    assert opening == ""
    parsed = yaml.safe_load(metadata)
    assert isinstance(parsed, dict)
    return parsed, body


def test_reference_capability_pages_match_the_approved_schema():
    paths = sorted(CAPABILITY_DIRECTORY.glob("*.md"))

    assert [path.name for path in paths] == [
        "isolated-execution.md",
        "model-routing.md",
        "tool-gateway.md",
    ]

    capabilities = []
    for path in paths:
        metadata, body = read_front_matter(path)
        capability = Capability.model_validate(metadata)
        capabilities.append(capability)
        for heading in REQUIRED_SECTIONS:
            assert heading in body

    assert len({capability.id for capability in capabilities}) == 3
    assert all(
        capability.lifecycle.value == "active"
        for capability in capabilities
    )
    assert all(
        capability.review.status.value == "approved"
        for capability in capabilities
    )
