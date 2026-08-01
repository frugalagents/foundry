"""Public orchestration entry point for R0.3 assurance outputs."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from pydantic import BaseModel

from ..deployable import build_deployable_solution
from ..engine import validate_workspace_revision
from ..models import ArchitectureWorkspace, CatalogRelease, content_hash
from .catalog import load_assurance_catalog
from .economics import build_economics_plan
from .models import AssuranceOutputs, SelectedBundleContext
from .outcomes import build_outcome_plan
from .readiness import build_decision_readiness
from .roadmap import build_implementation_roadmap
from .security import build_security_plan


def _coerce_bundle(
    selected_bundle: SelectedBundleContext | Mapping[str, object] | BaseModel | None,
) -> SelectedBundleContext | None:
    if selected_bundle is None or isinstance(
        selected_bundle, SelectedBundleContext
    ):
        return selected_bundle
    if isinstance(selected_bundle, BaseModel):
        selected_bundle = selected_bundle.model_dump(mode="json")
    return SelectedBundleContext.model_validate(selected_bundle)


def build_assurance_outputs(
    workspace: ArchitectureWorkspace,
    catalog: CatalogRelease,
    selected_bundle: (
        SelectedBundleContext | Mapping[str, object] | BaseModel | None
    ) = None,
    *,
    as_of: date,
) -> AssuranceOutputs:
    """Build one deterministic, content-addressed R0.3 assurance packet."""

    revision = workspace.revisions[-1]
    if revision.revision_id != workspace.current_revision_id:
        raise ValueError("workspace current revision is inconsistent")
    validate_workspace_revision(revision, catalog)

    bundle = _coerce_bundle(selected_bundle)
    active_component_ids = {
        node.component_id for node in revision.architecture.nodes
    }
    if bundle is not None:
        unknown_components = {
            item.component_id for item in bundle.implementations
        } - active_component_ids
        if unknown_components:
            raise ValueError(
                "selected bundle implements inactive components: "
                f"{sorted(unknown_components)}"
            )

    assurance_catalog = load_assurance_catalog(catalog, as_of=as_of)
    if bundle is not None:
        unknown_controls = {
            item.control_id for item in bundle.control_evidence
        } - {item.id for item in assurance_catalog.controls}
        unknown_costs = {
            item.cost_id for item in bundle.unit_cost_overrides
        } - {item.id for item in assurance_catalog.unit_costs}
        if unknown_controls or unknown_costs:
            raise ValueError(
                "selected bundle contains unknown assurance inputs: "
                f"controls={sorted(unknown_controls)}, "
                f"costs={sorted(unknown_costs)}"
            )
    security = build_security_plan(
        assurance_catalog,
        active_component_ids,
        selected_bundle=bundle,
        as_of=as_of,
    )
    roadmap = build_implementation_roadmap(
        catalog,
        revision,
        assurance_catalog,
        security,
        selected_bundle=bundle,
    )
    economics = build_economics_plan(
        revision,
        assurance_catalog,
        selected_bundle=bundle,
        as_of=as_of,
    )
    outcomes = build_outcome_plan(assurance_catalog)
    decision_matrix = build_deployable_solution(revision, catalog)
    readiness = build_decision_readiness(
        revision,
        catalog,
        decision_matrix,
        economics,
        security,
        selected_bundle_id=bundle.bundle_id if bundle is not None else None,
        as_of=as_of,
    )
    payload = {
        "schema_version": "3.0",
        "workspace_id": workspace.workspace_id,
        "workspace_revision_id": revision.revision_id,
        "workspace_state_hash": revision.state_hash,
        "architecture_catalog_id": catalog.id,
        "architecture_catalog_version": catalog.version,
        "architecture_catalog_content_hash": catalog.content_hash,
        "assurance_catalog_id": assurance_catalog.catalog_id,
        "assurance_catalog_version": assurance_catalog.version,
        "assurance_catalog_content_hash": assurance_catalog.content_hash,
        "selected_bundle_id": bundle.bundle_id if bundle is not None else None,
        "generated_as_of": as_of,
        "security": security,
        "roadmap": roadmap,
        "economics": economics,
        "outcomes": outcomes,
        "readiness": readiness,
    }
    hash_payload = {
        **payload,
        "generated_as_of": as_of.isoformat(),
        "security": security.model_dump(mode="json"),
        "roadmap": roadmap.model_dump(mode="json"),
        "economics": economics.model_dump(mode="json"),
        "outcomes": outcomes.model_dump(mode="json"),
        "readiness": readiness.model_dump(mode="json"),
    }
    return AssuranceOutputs(**payload, packet_hash=content_hash(hash_payload))
