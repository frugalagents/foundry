"""Versioned capability, control, and price catalogs."""
from __future__ import annotations

CATALOG_VERSION = "2026.07.28"
PRICE_CATALOG_DATE = "2026-07-28"
METHODOLOGY_VERSION = "2.0"


COMPONENTS: dict[str, dict] = {
    "identity": {
        "name": "Workload Identity and Access",
        "layer": "Foundation",
        "aws": ["IAM Identity Center", "AWS IAM", "Amazon Cognito"],
        "dependencies": [],
    },
    "gateway": {
        "name": "Model and Tool Gateway",
        "layer": "Control Plane",
        "aws": ["Amazon Bedrock AgentCore Gateway", "Amazon API Gateway"],
        "dependencies": ["identity"],
    },
    "policy": {
        "name": "Policy and Guardrail Engine",
        "layer": "Governance",
        "aws": ["Amazon Bedrock Guardrails", "AgentCore Policy", "AWS Organizations"],
        "dependencies": ["identity", "gateway"],
    },
    "registry": {
        "name": "Agent and Tool Registry",
        "layer": "Control Plane",
        "aws": ["Amazon Bedrock AgentCore Registry", "Amazon DynamoDB"],
        "dependencies": ["identity"],
    },
    "runtime": {
        "name": "Agent Runtime",
        "layer": "Runtime",
        "aws": ["Amazon Bedrock AgentCore Runtime", "AWS Lambda", "Amazon ECS"],
        "dependencies": ["identity"],
    },
    "sandbox": {
        "name": "Isolated Execution Sandbox",
        "layer": "Runtime",
        "aws": ["AgentCore Code Interpreter", "AWS Lambda"],
        "dependencies": ["runtime", "policy"],
    },
    "data_access": {
        "name": "Governed Data Access",
        "layer": "Data",
        "aws": ["Amazon Bedrock Knowledge Bases", "AWS Lake Formation", "Amazon S3"],
        "dependencies": ["identity", "policy"],
    },
    "observability": {
        "name": "Agent Observability and Evaluation",
        "layer": "AgentOps",
        "aws": ["Amazon CloudWatch", "AWS X-Ray", "AgentCore Evaluations"],
        "dependencies": ["runtime"],
    },
    "audit": {
        "name": "Immutable Audit Trail",
        "layer": "Governance",
        "aws": ["AWS CloudTrail", "Amazon S3 Object Lock", "AWS KMS"],
        "dependencies": ["identity"],
    },
    "deployment": {
        "name": "Agent Delivery Pipeline",
        "layer": "AgentOps",
        "aws": ["AWS CodePipeline", "AWS CodeBuild", "Amazon ECR"],
        "dependencies": ["registry", "policy"],
    },
    "tenant_control": {
        "name": "Tenant Isolation and Quotas",
        "layer": "Foundation",
        "aws": ["AWS Organizations", "AWS Control Tower", "Amazon API Gateway"],
        "dependencies": ["identity", "gateway"],
    },
    "resilience": {
        "name": "Multi-Region Resilience",
        "layer": "Foundation",
        "aws": ["Amazon Route 53", "AWS Global Accelerator", "Amazon DynamoDB Global Tables"],
        "dependencies": ["runtime", "observability"],
    },
    "metering": {
        "name": "Usage Metering and Entitlements",
        "layer": "Commercial",
        "aws": ["AWS Marketplace Metering Service", "Amazon EventBridge", "Amazon DynamoDB"],
        "dependencies": ["gateway", "identity"],
    },
}


BASE_COMPONENT_MONTHLY = {
    "identity": 300,
    "gateway": 650,
    "policy": 500,
    "registry": 250,
    "runtime": 900,
    "sandbox": 700,
    "data_access": 800,
    "observability": 600,
    "audit": 350,
    "deployment": 450,
    "tenant_control": 750,
    "resilience": 1800,
    "metering": 550,
}

# Transparent planning rates, not an AWS quote. Kept separate from architecture rules.
PLANNING_RATES = {
    "model_input_per_million_tokens": 3.0,
    "model_output_per_million_tokens": 15.0,
    "blended_model_per_million_tokens": 6.0,
    "gateway_per_million_requests": 3.5,
    "observability_per_million_events": 12.0,
}


REGULATION_CONTROLS: dict[str, list[dict]] = {
    "HIPAA": [
        {"id": "hipaa-encryption", "name": "PHI encryption and key isolation", "implementation": "AWS KMS plus service-level encryption"},
        {"id": "hipaa-audit", "name": "Six-year audit retention", "implementation": "CloudTrail and S3 Object Lock retention"},
        {"id": "hipaa-access", "name": "Minimum necessary access", "implementation": "IAM ABAC and Lake Formation"},
    ],
    "PCI-DSS": [
        {"id": "pci-segmentation", "name": "Cardholder-data segmentation", "implementation": "Dedicated accounts, VPC boundaries, and scoped IAM"},
        {"id": "pci-audit", "name": "Security event audit trail", "implementation": "CloudTrail, Security Hub, and immutable storage"},
    ],
    "SOX": [
        {"id": "sox-change", "name": "Controlled production changes", "implementation": "Approval-gated delivery pipeline and evidence retention"},
        {"id": "sox-access", "name": "Privileged-access review", "implementation": "IAM Identity Center and periodic access review"},
    ],
    "GDPR": [
        {"id": "gdpr-residency", "name": "Regional processing boundary", "implementation": "Region allow-list and data-location policy"},
        {"id": "gdpr-erasure", "name": "Deletion and retention workflows", "implementation": "Data lineage plus orchestrated erasure"},
    ],
    "EU-AI-ACT": [
        {"id": "euai-oversight", "name": "Human oversight and traceability", "implementation": "Approval policy, evaluation records, and audit trail"},
        {"id": "euai-risk", "name": "AI risk management evidence", "implementation": "Versioned evaluations, controls, and incident records"},
    ],
    "FEDRAMP": [
        {"id": "fedramp-boundary", "name": "Authorized service boundary", "implementation": "Eligible services in an approved AWS partition and region"},
        {"id": "fedramp-monitoring", "name": "Continuous monitoring", "implementation": "AWS Config, Security Hub, and evidence collection"},
    ],
    "SOC2": [
        {"id": "soc2-access", "name": "Logical access control", "implementation": "Central identity, least privilege, and access reviews"},
        {"id": "soc2-monitoring", "name": "Operational monitoring", "implementation": "CloudWatch alarms, incident workflow, and evidence retention"},
    ],
}
