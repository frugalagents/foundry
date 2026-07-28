"""Read-only metadata for inspecting the deterministic advisor engine."""
from __future__ import annotations

from advisor_core.catalogs import (
    BASE_COMPONENT_MONTHLY,
    CATALOG_VERSION,
    COMPONENTS,
    METHODOLOGY_VERSION,
    PRICE_CATALOG_DATE,
    REGULATION_CONTROLS,
)
from advisor_core.models import Workload
from advisor_core.questions import (
    BRANCH_QUESTIONS,
    QUESTIONNAIRE_VERSION,
    UNIVERSAL_QUESTIONS,
)


WORKLOAD_LABELS = {
    Workload.CODING: "Coding and developer productivity",
    Workload.INTERNAL_COPILOT: "Internal copilot",
    Workload.HOSTING: "Agent-hosting platform",
    Workload.CUSTOMER_FACING: "Customer-facing product",
    Workload.PROCESS_AUTOMATION: "Process automation",
    Workload.MARKETPLACE: "Agent marketplace",
}

DECISION_PIPELINE = [
    {
        "id": "evidence",
        "label": "Validate evidence",
        "description": "Reject decision-grade output when critical universal or workload evidence is missing.",
        "outputs": ["coverage", "evidence gaps"],
    },
    {
        "id": "ownership",
        "label": "Resolve ownership",
        "description": "Assign capability accountability and select the operating model.",
        "outputs": ["ownership matrix", "operating model"],
    },
    {
        "id": "requirements",
        "label": "Derive requirements",
        "description": "Translate risk, data, workload, and NFR evidence into hard architecture requirements.",
        "outputs": ["requirements", "assumptions"],
    },
    {
        "id": "topology",
        "label": "Select topology",
        "description": "Choose control plane, runtime placement, isolation boundary, and regional model.",
        "outputs": ["topology", "modifiers"],
    },
    {
        "id": "components",
        "label": "Activate components",
        "description": "Activate platform capabilities and AWS mappings from requirements and topology.",
        "outputs": ["components", "dependencies"],
    },
    {
        "id": "controls",
        "label": "Apply controls",
        "description": "Attach baseline, risk, isolation, and regulatory controls.",
        "outputs": ["controls", "residual risks"],
    },
    {
        "id": "delivery",
        "label": "Plan delivery",
        "description": "Build dependency-aware phases and workload-volume cost scenarios.",
        "outputs": ["roadmap", "cost range", "decision trace"],
    },
]

COMPONENT_ACTIVATION = {
    "identity": "Always active",
    "runtime": "Always active",
    "observability": "Always active",
    "deployment": "Always active",
    "gateway": "Action policy, approval, code boundary, or multitenancy",
    "policy": "Action policy, approval, or executable coding workload",
    "registry": "Hosting, marketplace, or secondary workloads",
    "sandbox": "Coding workload with command execution",
    "data_access": "Internal copilot or sensitive data",
    "audit": "Regulation, sensitive data, or marketplace trust",
    "tenant_control": "Multitenancy or infrastructure isolation",
    "resilience": "Availability or multi-region requirement",
    "metering": "Marketplace workload",
}


def _question(question: dict) -> dict:
    return {
        "id": question["id"],
        "path": question["path"],
        "prompt": question["prompt"],
        "type": question["type"],
        "unit": question.get("unit"),
        "critical": bool(question.get("critical")),
        "consumers": question.get("consumers", []),
    }


def build_engine_manifest() -> dict:
    branches = [
        {
            "workload": workload.value,
            "label": WORKLOAD_LABELS[workload],
            "question_count": len(BRANCH_QUESTIONS.get(workload, [])),
            "critical_count": sum(
                1 for question in BRANCH_QUESTIONS.get(workload, [])
                if question.get("critical")
            ),
            "questions": [
                _question(question)
                for question in BRANCH_QUESTIONS.get(workload, [])
            ],
        }
        for workload in Workload
    ]

    components = [
        {
            "id": component_id,
            "name": component["name"],
            "layer": component["layer"],
            "activation": COMPONENT_ACTIVATION[component_id],
            "dependencies": component["dependencies"],
            "aws_services": component["aws"],
            "monthly_planning_base_usd": BASE_COMPONENT_MONTHLY[component_id],
        }
        for component_id, component in COMPONENTS.items()
    ]
    components.sort(key=lambda item: (item["layer"], item["name"]))

    controls = [
        {
            "regime": regime,
            "control_count": len(items),
            "controls": items,
        }
        for regime, items in sorted(REGULATION_CONTROLS.items())
    ]

    branch_coverage = set(BRANCH_QUESTIONS) == set(Workload)
    dependency_integrity = all(
        dependency in COMPONENTS
        for component in COMPONENTS.values()
        for dependency in component["dependencies"]
    )
    cost_coverage = set(COMPONENTS) == set(BASE_COMPONENT_MONTHLY)
    traceability = all(
        question.get("consumers")
        for question in UNIVERSAL_QUESTIONS
    ) and all(
        question.get("consumers")
        for questions in BRANCH_QUESTIONS.values()
        for question in questions
    )

    return {
        "engine": {
            "name": "Platform Advisor Decision Engine",
            "schema_version": "2.0",
            "questionnaire_version": QUESTIONNAIRE_VERSION,
            "methodology_version": METHODOLOGY_VERSION,
            "catalog_version": CATALOG_VERSION,
            "price_catalog_date": PRICE_CATALOG_DATE,
            "execution_model": "deterministic",
            "llm_decision_authority": False,
        },
        "summary": {
            "workloads": len(Workload),
            "universal_questions": len(UNIVERSAL_QUESTIONS),
            "branch_questions": sum(len(items) for items in BRANCH_QUESTIONS.values()),
            "components": len(COMPONENTS),
            "regulatory_controls": sum(len(items) for items in REGULATION_CONTROLS.values()),
        },
        "pipeline": DECISION_PIPELINE,
        "questionnaire": {
            "universal": [_question(question) for question in UNIVERSAL_QUESTIONS],
            "branches": branches,
        },
        "catalog": {
            "components": components,
            "controls": controls,
        },
        "checks": [
            {
                "id": "branch-coverage",
                "label": "Every workload has a question branch",
                "ok": branch_coverage,
            },
            {
                "id": "dependency-integrity",
                "label": "Every component dependency resolves",
                "ok": dependency_integrity,
            },
            {
                "id": "cost-coverage",
                "label": "Every component has a planning cost",
                "ok": cost_coverage,
            },
            {
                "id": "question-traceability",
                "label": "Every question names its decision consumers",
                "ok": traceability,
            },
        ],
    }
