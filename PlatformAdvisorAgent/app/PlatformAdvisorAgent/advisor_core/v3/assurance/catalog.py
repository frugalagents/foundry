"""Loader and integrity checks for the isolated R0.3 assurance catalog."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from ..models import CatalogRelease, content_hash
from .models import AssuranceCatalog


CATALOG_PATH = Path(__file__).parent / "catalogs" / "coding-platform-r0.3"


class AssuranceCatalogError(ValueError):
    """Raised when assurance catalog artifacts are not publishable."""


def _unique(records: tuple[object, ...], kind: str) -> None:
    ids = [str(getattr(record, "id")) for record in records]
    if len(ids) != len(set(ids)):
        raise AssuranceCatalogError(f"duplicate {kind} IDs")


def load_assurance_catalog(
    architecture_catalog: CatalogRelease,
    *,
    as_of: date,
    path: str | Path = CATALOG_PATH,
) -> AssuranceCatalog:
    root = Path(path)
    files = sorted(root.glob("*.json"))
    if not files:
        raise AssuranceCatalogError(f"no assurance catalog files found in {root}")

    merged: dict[str, object] = {}
    for source_path in files:
        try:
            document = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssuranceCatalogError(
                f"invalid JSON in {source_path}: {exc.msg}"
            ) from exc
        for key, value in document.items():
            if key in merged:
                raise AssuranceCatalogError(
                    f"duplicate assurance catalog section {key!r}"
                )
            merged[key] = value

    effective_on = date.fromisoformat(str(merged["effective_on"]))
    if effective_on > as_of:
        raise AssuranceCatalogError(
            f"assurance catalog is not effective until {effective_on}"
        )

    payload = dict(merged)
    payload["content_hash"] = content_hash(merged)
    try:
        catalog = AssuranceCatalog.model_validate(payload)
    except (ValidationError, KeyError) as exc:
        raise AssuranceCatalogError(
            f"invalid assurance catalog contract: {exc}"
        ) from exc

    _unique(catalog.threats, "threat")
    _unique(catalog.controls, "control")
    _unique(catalog.best_practices, "best-practice")
    _unique(catalog.economic_assumptions, "economic-assumption")
    _unique(catalog.unit_costs, "unit-cost")
    _unique(catalog.outcome_events, "outcome-event")
    _unique(catalog.outcome_metrics, "outcome-metric")

    component_ids = {item.id for item in architecture_catalog.components}
    threat_ids = {item.id for item in catalog.threats}
    control_ids = {item.id for item in catalog.controls}
    event_ids = {item.id for item in catalog.outcome_events}

    for threat in catalog.threats:
        missing = set(threat.component_ids) - component_ids
        if missing:
            raise AssuranceCatalogError(
                f"threat {threat.id} references missing components {sorted(missing)}"
            )
    for control in catalog.controls:
        missing_threats = set(control.threat_ids) - threat_ids
        missing_components = set(control.component_ids) - component_ids
        if missing_threats or missing_components:
            raise AssuranceCatalogError(
                f"control {control.id} has dangling references"
            )
    for practice in catalog.best_practices:
        if (
            set(practice.control_ids) - control_ids
            or set(practice.component_ids) - component_ids
        ):
            raise AssuranceCatalogError(
                f"best practice {practice.id} has dangling references"
            )
    for metric in catalog.outcome_metrics:
        if set(metric.source_event_ids) - event_ids:
            raise AssuranceCatalogError(
                f"metric {metric.id} references missing events"
            )
    return catalog
