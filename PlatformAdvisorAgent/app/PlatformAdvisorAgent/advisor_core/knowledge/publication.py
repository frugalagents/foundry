"""Publication authorization boundaries for knowledge and catalog releases."""
from __future__ import annotations

from pydantic import Field

from .contradictions import ContradictionReport, ContradictionSeverity
from .models import FrozenModel, StableId, StrEnum
from .review_workflow import KnowledgeReviewRecord, KnowledgeReviewState


class PrincipalType(StrEnum):
    RESEARCH_AGENT = "research_agent"
    HUMAN_REVIEWER = "human_reviewer"
    RELEASE_PIPELINE = "release_pipeline"


class PublicationAction(StrEnum):
    WRITE_CANDIDATE = "write_candidate"
    WRITE_REVIEW_BUNDLE = "write_review_bundle"
    RECORD_REVIEW_DECISION = "record_review_decision"
    PUBLISH_KNOWLEDGE = "publish_knowledge"
    PUBLISH_CATALOG = "publish_catalog"


class PublicationAuthorizationError(PermissionError):
    pass


class PublicationPrincipal(FrozenModel):
    principal_id: StableId
    principal_type: PrincipalType


class PublicationAuthorization(FrozenModel):
    principal_id: StableId
    principal_type: PrincipalType
    action: PublicationAction
    authorized: bool
    reason: str = Field(min_length=1)


PERMISSIONS: dict[PrincipalType, frozenset[PublicationAction]] = {
    PrincipalType.RESEARCH_AGENT: frozenset(
        {
            PublicationAction.WRITE_CANDIDATE,
            PublicationAction.WRITE_REVIEW_BUNDLE,
        }
    ),
    PrincipalType.HUMAN_REVIEWER: frozenset(
        {
            PublicationAction.RECORD_REVIEW_DECISION,
        }
    ),
    PrincipalType.RELEASE_PIPELINE: frozenset(
        {
            PublicationAction.PUBLISH_KNOWLEDGE,
            PublicationAction.PUBLISH_CATALOG,
        }
    ),
}


def authorize_publication(
    principal: PublicationPrincipal,
    action: PublicationAction | str,
    *,
    review_records: tuple[KnowledgeReviewRecord, ...] = (),
    contradiction_report: ContradictionReport | None = None,
) -> PublicationAuthorization:
    """Authorize one action without granting a broader publication capability."""

    action = PublicationAction(action)
    if action not in PERMISSIONS[principal.principal_type]:
        return PublicationAuthorization(
            principal_id=principal.principal_id,
            principal_type=principal.principal_type,
            action=action,
            authorized=False,
            reason=(
                f"{principal.principal_type.value} is not permitted to "
                f"{action.value}"
            ),
        )

    if action in {
        PublicationAction.PUBLISH_KNOWLEDGE,
        PublicationAction.PUBLISH_CATALOG,
    }:
        if not review_records:
            return PublicationAuthorization(
                principal_id=principal.principal_id,
                principal_type=principal.principal_type,
                action=action,
                authorized=False,
                reason="publication requires approved review records",
            )
        non_approved = [
            record.candidate_id
            for record in review_records
            if record.state is not KnowledgeReviewState.APPROVED
        ]
        if non_approved:
            return PublicationAuthorization(
                principal_id=principal.principal_id,
                principal_type=principal.principal_type,
                action=action,
                authorized=False,
                reason=(
                    "publication requires approved candidates: "
                    + ", ".join(sorted(non_approved))
                ),
            )
        if contradiction_report is None:
            return PublicationAuthorization(
                principal_id=principal.principal_id,
                principal_type=principal.principal_type,
                action=action,
                authorized=False,
                reason="publication requires a contradiction report",
            )
        blocking = [
            contradiction
            for contradiction in contradiction_report.contradictions
            if contradiction.severity is ContradictionSeverity.BLOCKING
        ]
        if blocking:
            return PublicationAuthorization(
                principal_id=principal.principal_id,
                principal_type=principal.principal_type,
                action=action,
                authorized=False,
                reason="publication is blocked by unresolved contradictions",
            )

    return PublicationAuthorization(
        principal_id=principal.principal_id,
        principal_type=principal.principal_type,
        action=action,
        authorized=True,
        reason="action satisfies the least-privilege publication policy",
    )


def require_publication_authorization(
    principal: PublicationPrincipal,
    action: PublicationAction | str,
    *,
    review_records: tuple[KnowledgeReviewRecord, ...] = (),
    contradiction_report: ContradictionReport | None = None,
) -> PublicationAuthorization:
    authorization = authorize_publication(
        principal,
        action,
        review_records=review_records,
        contradiction_report=contradiction_report,
    )
    if not authorization.authorized:
        raise PublicationAuthorizationError(authorization.reason)
    return authorization
