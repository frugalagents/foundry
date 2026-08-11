"""GitHub release and security-advisory collection."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from pydantic import Field, field_validator

from .collection import CollectionError, DEFAULT_TIMEOUT_SECONDS, USER_AGENT
from .models import FrozenModel, StableId, content_hash
from .source_registry import CollectorType, SourceRegistryEntry


GITHUB_API_ROOT = "https://api.github.com"
GITHUB_ACCEPT = "application/vnd.github+json"
GITHUB_API_VERSION = "2022-11-28"


class GitReleaseRecord(FrozenModel):
    release_id: str = Field(min_length=1)
    tag_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    changelog: str
    html_uri: str = Field(min_length=1)
    target_commitish: str = Field(min_length=1)
    target_object_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    target_object_type: str = Field(pattern=r"^(commit|tag)$")
    draft: bool
    prerelease: bool
    published_at: datetime
    updated_at: datetime


class GitSecurityAdvisoryRecord(FrozenModel):
    advisory_id: str = Field(pattern=r"^GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}$")
    cve_id: str | None = Field(default=None, pattern=r"^CVE-\d{4}-\d{4,}$")
    summary: str = Field(min_length=1)
    description: str
    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    published_at: datetime
    updated_at: datetime
    withdrawn_at: datetime | None = None
    affected_packages: tuple[str, ...] = ()

    @field_validator("affected_packages")
    @classmethod
    def unique_packages(
        cls,
        packages: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(packages) != len(set(packages)):
            raise ValueError("affected packages must be unique")
        return tuple(sorted(packages))


class GitRepositorySnapshot(FrozenModel):
    snapshot_id: StableId
    source_id: StableId
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    retrieved_at: datetime
    releases: tuple[GitReleaseRecord, ...]
    security_advisories: tuple[GitSecurityAdvisoryRecord, ...]
    collection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("releases")
    @classmethod
    def unique_sorted_releases(
        cls,
        releases: tuple[GitReleaseRecord, ...],
    ) -> tuple[GitReleaseRecord, ...]:
        tags = [release.tag_name for release in releases]
        if len(tags) != len(set(tags)):
            raise ValueError("release tags must be unique")
        return tuple(sorted(releases, key=lambda release: release.tag_name))

    @field_validator("security_advisories")
    @classmethod
    def unique_sorted_advisories(
        cls,
        advisories: tuple[GitSecurityAdvisoryRecord, ...],
    ) -> tuple[GitSecurityAdvisoryRecord, ...]:
        identifiers = [advisory.advisory_id for advisory in advisories]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("security advisory IDs must be unique")
        return tuple(
            sorted(advisories, key=lambda advisory: advisory.advisory_id)
        )


JsonFetcher = Callable[[str, dict[str, str], float], object]


def _fetch_json(
    uri: str,
    headers: dict[str, str],
    timeout_seconds: float,
) -> object:
    request = Request(uri, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            if status < 200 or status > 299:
                raise CollectionError(
                    f"GitHub API returned HTTP status {status}"
                )
            return json.loads(response.read())
    except CollectionError:
        raise
    except (OSError, ValueError) as error:
        raise CollectionError(f"GitHub API request failed: {error}") from error


def github_repository_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise CollectionError("Git release source must use github.com over HTTPS")
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) < 2:
        raise CollectionError("GitHub source URI must identify a repository")
    return f"{segments[0]}/{segments[1]}"


def _require_list(payload: object, label: str) -> list[dict[str, object]]:
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise CollectionError(f"GitHub {label} response must be a list")
    return payload


def _require_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise CollectionError(f"GitHub {label} response must be an object")
    return payload


def _resolve_tag_target(
    repository: str,
    tag_name: str,
    *,
    fetch_json: JsonFetcher,
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[str, str]:
    encoded_tag = quote(tag_name, safe="")
    reference = _require_dict(
        fetch_json(
            f"{GITHUB_API_ROOT}/repos/{repository}/git/ref/tags/{encoded_tag}",
            headers,
            timeout_seconds,
        ),
        "tag reference",
    )
    target = _require_dict(reference.get("object"), "tag target")
    target_sha = str(target.get("sha", ""))
    target_type = str(target.get("type", ""))
    if target_type == "tag":
        annotated = _require_dict(
            fetch_json(
                f"{GITHUB_API_ROOT}/repos/{repository}/git/tags/{target_sha}",
                headers,
                timeout_seconds,
            ),
            "annotated tag",
        )
        target = _require_dict(annotated.get("object"), "annotated tag target")
        target_sha = str(target.get("sha", ""))
        target_type = str(target.get("type", ""))
    if target_type != "commit":
        raise CollectionError(
            f"tag {tag_name} does not resolve to a commit"
        )
    return target_sha, target_type


def _release_record(
    repository: str,
    payload: dict[str, object],
    *,
    fetch_json: JsonFetcher,
    headers: dict[str, str],
    timeout_seconds: float,
) -> GitReleaseRecord:
    tag_name = str(payload.get("tag_name", ""))
    target_sha, target_type = _resolve_tag_target(
        repository,
        tag_name,
        fetch_json=fetch_json,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    return GitReleaseRecord(
        release_id=str(payload.get("id", "")),
        tag_name=tag_name,
        title=str(payload.get("name") or tag_name),
        changelog=str(payload.get("body") or ""),
        html_uri=str(payload.get("html_url", "")),
        target_commitish=str(payload.get("target_commitish", "")),
        target_object_sha=target_sha,
        target_object_type=target_type,
        draft=bool(payload.get("draft", False)),
        prerelease=bool(payload.get("prerelease", False)),
        published_at=payload.get("published_at"),
        updated_at=payload.get("updated_at"),
    )


def _advisory_record(
    payload: dict[str, object],
) -> GitSecurityAdvisoryRecord:
    vulnerabilities = payload.get("vulnerabilities") or []
    if not isinstance(vulnerabilities, list):
        raise CollectionError(
            "GitHub advisory vulnerabilities must be a list"
        )
    affected_packages = []
    for vulnerability in vulnerabilities:
        if not isinstance(vulnerability, dict):
            raise CollectionError(
                "GitHub advisory vulnerability must be an object"
            )
        package = vulnerability.get("package") or {}
        if not isinstance(package, dict):
            raise CollectionError(
                "GitHub advisory package must be an object"
            )
        ecosystem = str(package.get("ecosystem", "unknown")).lower()
        name = str(package.get("name", "unknown"))
        affected_packages.append(f"{ecosystem}:{name}")
    return GitSecurityAdvisoryRecord(
        advisory_id=str(payload.get("ghsa_id", "")),
        cve_id=payload.get("cve_id"),
        summary=str(payload.get("summary", "")),
        description=str(payload.get("description") or ""),
        severity=str(payload.get("severity", "")).lower(),
        published_at=payload.get("published_at"),
        updated_at=payload.get("updated_at"),
        withdrawn_at=payload.get("withdrawn_at"),
        affected_packages=tuple(affected_packages),
    )


def collect_github_releases(
    source: SourceRegistryEntry,
    *,
    retrieved_at: datetime,
    fetch_json: JsonFetcher = _fetch_json,
    token: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> GitRepositorySnapshot:
    """Collect releases, resolved tag commits, and repository advisories."""

    if not source.enabled:
        raise CollectionError("source collection is disabled")
    if source.collector not in {
        CollectorType.GITHUB_RELEASES,
        CollectorType.GITHUB_REPOSITORY,
    }:
        raise CollectionError(
            f"collector {source.collector.value} is not GitHub-compatible"
        )

    repository = github_repository_from_uri(str(source.base_uri))
    headers = {
        "Accept": GITHUB_ACCEPT,
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    releases_payload = _require_list(
        fetch_json(
            f"{GITHUB_API_ROOT}/repos/{repository}/releases?per_page=100",
            headers,
            timeout_seconds,
        ),
        "releases",
    )
    advisories_payload = _require_list(
        fetch_json(
            (
                f"{GITHUB_API_ROOT}/repos/{repository}"
                "/security-advisories?per_page=100"
            ),
            headers,
            timeout_seconds,
        ),
        "security advisories",
    )
    releases = tuple(
        _release_record(
            repository,
            payload,
            fetch_json=fetch_json,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        for payload in releases_payload
    )
    advisories = tuple(
        _advisory_record(payload) for payload in advisories_payload
    )
    collection_payload = {
        "source_id": source.id,
        "repository": repository,
        "retrieved_at": retrieved_at.isoformat(),
        "releases": [
            release.model_dump(mode="json") for release in releases
        ],
        "security_advisories": [
            advisory.model_dump(mode="json") for advisory in advisories
        ],
    }
    collection_hash = content_hash(collection_payload)
    source_slug = source.id.split(":", 1)[1]
    return GitRepositorySnapshot(
        snapshot_id=(
            f"snapshot:{source_slug}-{collection_hash[7:19]}"
        ),
        source_id=source.id,
        repository=repository,
        retrieved_at=retrieved_at,
        releases=releases,
        security_advisories=advisories,
        collection_hash=collection_hash,
    )
