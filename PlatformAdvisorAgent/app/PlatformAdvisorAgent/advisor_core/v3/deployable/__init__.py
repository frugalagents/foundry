"""Public R0.2 deployable-solution builder contract."""

from .builder import build_deployable_solution
from .catalog import (
    DEFAULT_CATALOG_PATH,
    DeployableCatalogCompilationError,
    compile_deployable_catalog,
    load_deployable_documents,
)
from .models import (
    CandidateBundle,
    CompatibilityFinding,
    CompatibilityStatus,
    DeployableCatalogRelease,
    DeployableDecisionMatrix,
    ProviderClass,
    Recommendation,
    RecommendationState,
    SensitivityIndicator,
    ServiceVariant,
)

__all__ = [
    "CandidateBundle",
    "CompatibilityFinding",
    "CompatibilityStatus",
    "DEFAULT_CATALOG_PATH",
    "DeployableCatalogCompilationError",
    "DeployableCatalogRelease",
    "DeployableDecisionMatrix",
    "ProviderClass",
    "Recommendation",
    "RecommendationState",
    "SensitivityIndicator",
    "ServiceVariant",
    "build_deployable_solution",
    "compile_deployable_catalog",
    "load_deployable_documents",
]
