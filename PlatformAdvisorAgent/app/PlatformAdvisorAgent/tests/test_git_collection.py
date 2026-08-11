from __future__ import annotations

from datetime import datetime, timezone

import pytest

from advisor_core.knowledge import (
    CollectionError,
    ReviewMetadata,
    SourceRegistryEntry,
    SourceTerms,
    collect_github_releases,
    github_repository_from_uri,
)


RETRIEVED_AT = datetime(2026, 8, 11, 15, tzinfo=timezone.utc)
REPOSITORY = "example/project"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
COMMIT_SHA = "a" * 40
ANNOTATED_TAG_SHA = "b" * 40


def enabled_source(**overrides) -> SourceRegistryEntry:
    values = {
        "id": "source:example-project-releases",
        "name": "Example project releases",
        "publisher": "Example",
        "source_class": "maintainer_release_repository",
        "base_uri": f"https://github.com/{REPOSITORY}/releases",
        "owner_id": "team:platform-advisor",
        "authority_tier": "tier_b_operational_guidance",
        "cadence": "on_release",
        "collector": "github_releases",
        "parser": "markdown",
        "freshness_days": 7,
        "enabled": True,
        "terms": SourceTerms(
            status="approved",
            allows_automated_collection=True,
            allows_snapshot_retention=True,
            allows_derivative_claims=True,
            review=ReviewMetadata(
                status="approved",
                reviewer_ids=("person:source-reviewer",),
                reviewed_at=RETRIEVED_AT,
            ),
        ),
    }
    values.update(overrides)
    return SourceRegistryEntry(**values)


def github_payloads():
    return {
        f"{API_ROOT}/releases?per_page=100": [
            {
                "id": 101,
                "tag_name": "v2.0.0",
                "name": "Version 2",
                "body": "Adds governed tool execution.",
                "html_url": (
                    f"https://github.com/{REPOSITORY}/releases/tag/v2.0.0"
                ),
                "target_commitish": "main",
                "draft": False,
                "prerelease": False,
                "published_at": "2026-08-10T10:00:00Z",
                "updated_at": "2026-08-10T11:00:00Z",
            }
        ],
        f"{API_ROOT}/git/ref/tags/v2.0.0": {
            "object": {
                "sha": ANNOTATED_TAG_SHA,
                "type": "tag",
            }
        },
        f"{API_ROOT}/git/tags/{ANNOTATED_TAG_SHA}": {
            "object": {
                "sha": COMMIT_SHA,
                "type": "commit",
            }
        },
        f"{API_ROOT}/security-advisories?per_page=100": [
            {
                "ghsa_id": "GHSA-2345-6789-cfgh",
                "cve_id": "CVE-2026-12345",
                "summary": "Tool input validation bypass",
                "description": "A crafted tool input bypasses validation.",
                "severity": "high",
                "published_at": "2026-08-09T10:00:00Z",
                "updated_at": "2026-08-10T12:00:00Z",
                "withdrawn_at": None,
                "vulnerabilities": [
                    {
                        "package": {
                            "ecosystem": "pip",
                            "name": "example-project",
                        }
                    }
                ],
            }
        ],
    }


def test_git_collection_captures_release_commit_and_advisory_changes():
    payloads = github_payloads()

    snapshot = collect_github_releases(
        enabled_source(),
        retrieved_at=RETRIEVED_AT,
        fetch_json=lambda uri, headers, timeout: payloads[uri],
    )

    assert snapshot.repository == REPOSITORY
    assert len(snapshot.releases) == 1
    release = snapshot.releases[0]
    assert release.tag_name == "v2.0.0"
    assert release.changelog == "Adds governed tool execution."
    assert release.target_commitish == "main"
    assert release.target_object_sha == COMMIT_SHA
    assert release.target_object_type == "commit"
    assert len(snapshot.security_advisories) == 1
    advisory = snapshot.security_advisories[0]
    assert advisory.advisory_id == "GHSA-2345-6789-cfgh"
    assert advisory.updated_at.isoformat() == "2026-08-10T12:00:00+00:00"
    assert advisory.affected_packages == ("pip:example-project",)
    assert snapshot.collection_hash.startswith("sha256:")


def test_git_collection_is_deterministic():
    payloads = github_payloads()
    fetch = lambda uri, headers, timeout: payloads[uri]

    first = collect_github_releases(
        enabled_source(),
        retrieved_at=RETRIEVED_AT,
        fetch_json=fetch,
    )
    second = collect_github_releases(
        enabled_source(),
        retrieved_at=RETRIEVED_AT,
        fetch_json=fetch,
    )

    assert first == second


def test_github_repository_parser_rejects_non_github_hosts():
    with pytest.raises(
        CollectionError,
        match="must use github.com over HTTPS",
    ):
        github_repository_from_uri(
            "https://git.example.com/example/project/releases"
        )


def test_git_collection_rejects_disabled_source():
    with pytest.raises(CollectionError, match="source collection is disabled"):
        collect_github_releases(
            enabled_source(enabled=False),
            retrieved_at=RETRIEVED_AT,
            fetch_json=lambda uri, headers, timeout: [],
        )
