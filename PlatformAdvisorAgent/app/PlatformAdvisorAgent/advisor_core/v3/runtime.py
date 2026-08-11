"""Production workspace construction from one verified knowledge release."""
from __future__ import annotations

from datetime import date, datetime, time, timezone

from advisor_core.knowledge.runtime_release import (
    LoadedKnowledgeRelease,
    get_configured_knowledge_release,
)

from .engine import apply_requirement_patch, initialize_workspace
from .models import (
    ArchitectureWorkspace,
    AssumptionMetadata,
    CatalogRelease,
    RequirementConstraint,
    RequirementPatch,
)


CODING_PLATFORM_WORKING_ASSUMPTIONS = {
    "requirement:action-approval": True,
    "requirement:approved-package-registries": True,
    "requirement:approved-regions": "any-approved",
    "requirement:asynchronous-tasks": True,
    "requirement:concurrent-agent-tasks": 1000,
    "requirement:developer-count": 5000,
    "requirement:enterprise-identity": "entra",
    "requirement:execution-placement": "hybrid",
    "requirement:multi-agent": False,
    "requirement:multi-model-provider": True,
    "requirement:outcome-observability": True,
    "requirement:restricted-egress": True,
    "requirement:source-control": "gitlab-saas",
    "requirement:team-boundaries": True,
    "requirement:warm-runtime-capacity": True,
}


def build_workspace_from_catalog(
    catalog: CatalogRelease,
    *,
    as_of: date,
    workspace_id: str,
    requirement_values: dict[str, object] | None = None,
) -> ArchitectureWorkspace:
    """Apply explicit answers over the reviewed working-assumption baseline."""

    recorded_at = datetime.combine(as_of, time(12, 0), tzinfo=timezone.utc)
    workspace = initialize_workspace(
        catalog,
        workspace_id=workspace_id,
        created_at=recorded_at,
    )
    initial = workspace.revisions[-1]
    user_values = requirement_values or {}
    values = {**CODING_PLATFORM_WORKING_ASSUMPTIONS, **user_values}
    patch = RequirementPatch(
        patch_id="patch:enterprise-coding-platform",
        base_revision_number=initial.revision_number,
        changes=tuple(
            RequirementConstraint(
                requirement_id=requirement_id,
                value=value,
                source=(
                    "user"
                    if requirement_id in user_values
                    else "assumption"
                ),
                assumption=(
                    None
                    if requirement_id in user_values
                    else AssumptionMetadata(
                        rationale=(
                            "Working demonstration baseline pending customer "
                            "confirmation."
                        ),
                        confidence=0.6,
                        owner="Platform Advisor product team",
                        source="Coding-platform demonstration baseline",
                    )
                ),
                recorded_at=recorded_at,
            )
            for requirement_id, value in sorted(values.items())
        ),
        rationale=(
            "Apply demonstration assumptions and any explicit user requirements."
        ),
    )
    return apply_requirement_patch(
        workspace,
        patch,
        catalog,
        created_at=recorded_at,
    )


def build_runtime_workspace(
    as_of: date,
    *,
    workspace_id: str,
    requirement_values: dict[str, object] | None = None,
    release: LoadedKnowledgeRelease | None = None,
) -> tuple[LoadedKnowledgeRelease, ArchitectureWorkspace]:
    pinned = release or get_configured_knowledge_release()
    workspace = build_workspace_from_catalog(
        pinned.logical_catalog,
        as_of=as_of,
        workspace_id=workspace_id,
        requirement_values=requirement_values,
    )
    return pinned, workspace
