from __future__ import annotations

from collections import Counter
from pathlib import Path

from advisor_core.knowledge import load_source_registry


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SOURCE_REGISTRY_PATH = (
    REPOSITORY_ROOT / "knowledge" / "sources" / "initial-portfolio.yaml"
)
IMPLEMENTATION_ECOSYSTEMS = (
    "ecosystem-aws",
    "ecosystem-github",
    "ecosystem-gitlab",
)


def test_initial_source_portfolio_has_required_authority_and_coverage():
    registry = load_source_registry(SOURCE_REGISTRY_PATH)

    assert 30 <= len(registry.sources) <= 50
    assert {
        source.authority_tier.value for source in registry.sources
    } <= {
        "tier_a_decision_authority",
        "tier_b_operational_guidance",
    }

    coverage = Counter(
        tag
        for source in registry.sources
        for tag in source.tags
        if tag in IMPLEMENTATION_ECOSYSTEMS
    )
    for ecosystem in IMPLEMENTATION_ECOSYSTEMS:
        assert coverage[ecosystem] >= 8


def test_initial_sources_fail_closed_pending_terms_review():
    registry = load_source_registry(SOURCE_REGISTRY_PATH)

    assert all(not source.enabled for source in registry.sources)
    assert all(
        source.terms.status.value == "review_required"
        for source in registry.sources
    )
    assert all(
        source.health.status.value == "never_checked"
        for source in registry.sources
    )
