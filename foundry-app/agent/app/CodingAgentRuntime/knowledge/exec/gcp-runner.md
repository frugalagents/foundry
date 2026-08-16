---
type: platform-component
title: GCP Runner
description: deploying and operating coding agent execution on Google Cloud Platform — Cloud Run, Workload Identity Federation, GCP-native observability, and hybrid AWS-GCP platform topologies for enterprises with a material GCP footprint
group: exec
tags: [exec, gcp, cloud-run, workload-identity, gcp-runner, hybrid-cloud, vertex-ai, artifact-registry, cloud-logging]
timestamp: 2026-08-15T00:00:00Z
status: candidate
traversal: conditional
trigger: [gcp, google-cloud, cloud-run, gke, vertex-ai, gcp-runner, hybrid-aws-gcp, workload-identity-federation, industrial-automation-gcp, gcp-primary]
decision-question: "Does a material developer population work primarily in a GCP environment — GCP-hosted CI/CD, GCP-based artifact registries, Vertex AI as the primary model platform, or GCP-first BUs acquired or operated separately — where deploying the agent runtime exclusively on AWS would create friction or policy gaps?"
---

GCP runners address the hybrid-cloud reality at large enterprises: most coding
agent platforms anchor on AWS (IAM Identity Center, Bedrock, CloudWatch) but
a significant developer population works in GCP — GCP-based CI/CD pipelines,
GKE workloads, Vertex AI model development, Cloud Build, or GCP-first subsidiary
businesses. Forcing these developers onto an AWS-centric runner creates friction
(cross-cloud auth, latency, policy enforcement gaps) and shadow-IT risk.

The GCP runner is a first-class execution surface that:
- Runs agent execution (harness + MCP server) on Cloud Run or GKE
- Authenticates to GCP resources natively via Workload Identity Federation
- Routes model inference to Bedrock (cross-cloud, for Claude access) or Vertex AI
  (for GCP-native model serving)
- Feeds session logs to Cloud Logging / Security Command Center for GCP-native SIEM
- Participates in the federated platform governance model (OPA bundle server,
  DynamoDB instance registry)

## Architecture

```
Developer (GCP environment)
  └── GCP Runner (Cloud Run service or GKE pod)
        ├── Agent harness (Strands / LangChain on Cloud Run)
        ├── MCP server (Cloud Run sidecar or co-deployed service)
        ├── Workload Identity Federation → GCP IAM
        │     ├── Access Cloud Build, Artifact Registry, GCS
        │     └── Access GKE cluster API (for GKE-resident teams)
        ├── Cross-cloud model inference
        │     ├── Option A: Bedrock (us-east-1) via VPC-to-VPC or internet
        │     └── Option B: Vertex AI (us-central1 or region-matched)
        └── Observability
              ├── Cloud Logging → Cloud Log Router → SIEM
              └── Cloud Monitoring metrics → Looker Studio / Grafana
```

The GCP runner connects to the same MCP gateway and OPA policy bundle as the
AWS runner — policy enforcement is identical regardless of which runner a
developer uses.

## Decisions

**Where does the GCP runner execute?**
- Cloud Run (recommended for most deployments) — serverless container execution;
  scales to zero between sessions; no cluster management; CPU/memory configurable
  per session; minimum instances set to avoid cold starts on first session; Cloud
  Run supports VPC connector for private GCP resource access; simplest operational
  model for a platform team primarily experienced in AWS
- GKE (for organizations already running GKE at scale) — agent harness runs as
  a Kubernetes pod; Workload Identity bound to the pod's service account; can
  co-locate with GKE-native developer tooling; requires GKE cluster maintenance;
  appropriate when the organization has dedicated GKE platform engineering capacity
- Cloud Run Jobs (for async / batch tasks) — if the agent is used for longer
  batch operations (repository-wide refactoring, documentation generation across
  many files), Cloud Run Jobs provides a better execution model than long-running
  HTTP-triggered services; job execution is isolated per task; logs are job-scoped

**How does the GCP runner authenticate to GCP resources?**
- Workload Identity Federation (recommended) — bind the Cloud Run service account
  to a GCP IAM service account; grant IAM roles on the service account for required
  GCP resources (Source Repositories, Artifact Registry, Cloud Build, GCS); no
  service account key files anywhere; authentication is automatic via the metadata
  server; the service account has only the IAM roles required by the tools the
  agent uses
- Service account key (avoid) — exporting a JSON key and mounting it as a secret;
  creates a long-lived credential that can be leaked; only acceptable for local
  development testing; never for production Cloud Run services
- Workload Identity Federation from AWS (for cross-cloud) — if the platform's
  identity anchor is AWS IAM Identity Center but the runner is on GCP, configure
  GCP Workload Identity Federation to trust the AWS OIDC provider; the runner
  presents its AWS IAM role token to GCP WIF to exchange for a GCP access token;
  enables a single identity chain across AWS and GCP without static credentials

**Which model provider does the GCP runner use?**
- Amazon Bedrock (cross-cloud, Claude access) — for organizations standardizing
  on Claude; the GCP runner makes HTTPS calls to the Bedrock endpoint in the
  nearest AWS region; latency is typically 20-60ms additional for the cross-cloud
  hop; acceptable for interactive use; requires outbound internet or Cloud VPN
  to AWS VPC; authenticate via cross-cloud IAM (AWS access key stored in Secret
  Manager, or Workload Identity Federation from GCP to AWS)
- Vertex AI (GCP-native, Gemini models) — for organizations standardizing on
  Gemini or where data residency requirements prohibit cross-cloud traffic; Vertex
  AI supports Gemini Pro/Ultra and third-party models via Model Garden; no cross-cloud
  hop; authentication via Workload Identity; appropriate for GCP-primary BUs with
  data locality requirements
- Hybrid routing — the MCP gateway routes inference requests based on the model
  requested; Claude requests route to Bedrock; Gemini requests route to Vertex AI;
  enables model flexibility without forcing a single provider; the gateway abstracts
  the routing from the agent harness

**How does the GCP runner integrate with GCP-native developer tools?**
- Cloud Source Repositories / Cloud Build — MCP tools for triggering builds, reading
  build logs, and fetching source are analogous to the GitHub MCP tools on AWS;
  bind the service account to `roles/source.reader` and `roles/cloudbuild.builds.viewer`;
  restrict write access (trigger build, cancel build) to explicit allowlist
- Artifact Registry — read access for the agent to inspect container images, package
  versions, and build artifacts; bind to `roles/artifactregistry.reader`; never
  bind write or delete permissions to the agent service account
- GKE cluster API — for teams running GKE workloads, the agent may need to read
  cluster state (describe deployments, get pod logs); bind to a custom role with
  read-only cluster scope; never cluster-admin or write access
- BigQuery (for data scientists) — read-only access to datasets the developer's
  project owns; useful for JupyterLab-on-GCP scenarios where the agent reads
  schema and sample rows to inform code generation

**How are GCP runner session logs integrated with the platform audit trail?**
- Cloud Logging → Log Router → central SIEM — session events (session start/end,
  tool calls, model invocations) written to Cloud Logging via the standard Python
  logging library; Cloud Log Router exports to the organization's SIEM (Splunk,
  Chronicle, Security Command Center); log entries include `session_id`, `developer_id`,
  `instance_id`, `tool_name` fields for correlation with the AWS runner logs
- OCSF normalization — log events are structured in OCSF format before writing
  to Cloud Logging; this ensures GCP runner logs can be ingested into Security
  Lake (which uses OCSF) alongside AWS runner logs; a Cloud Run sidecar normalizes
  log format on write
- Cloud Audit Logs for GCP resource access — all GCP resource API calls made by
  the service account are captured in Cloud Audit Logs automatically; no additional
  instrumentation required; audit logs feed into Security Command Center for threat
  detection

**How is the GCP runner governed by the federated platform policy?**
- OPA bundle fetch at startup — the Cloud Run service fetches the current OPA policy
  bundle from the platform's OPA bundle server (S3 + CloudFront) at startup; the
  bundle is cached in the container's memory for the session; policy evaluation
  is local (no network call per tool use); the bundle version is logged as part
  of the session metadata
- Instance registry registration — at startup, the GCP runner instance registers
  itself in the platform's DynamoDB instance registry with its GCP region, BU tag,
  and current OPA bundle version; the hub governance dashboard shows GCP instances
  alongside AWS instances; drift detection applies equally
- Policy canon applies — the OPA bundle's floor policy (no unscoped repo access,
  no write without approval gate, no export-control repo access without US-person
  claim) applies to GCP runner sessions exactly as to AWS runner sessions; the
  GCP runner cannot be a governance gap

## Principles

- The GCP runner is a first-class citizen, not a second-class workaround — it
  must enforce the same policies, produce the same audit trail format, and
  participate in the same governance model as the AWS runner; a GCP runner that
  is less governed than the AWS runner creates an arbitrage path for developers
  who want to avoid controls
- Workload Identity, not service account keys — there is no acceptable reason to
  use a service account key file in a production Cloud Run deployment; Workload
  Identity is the correct pattern and is simpler to manage once configured; any
  design that requires exporting a key should be treated as a design defect
- Cross-cloud model calls must be audited — if the GCP runner calls Bedrock for
  inference, those calls must be logged (request ID, model ID, token counts) in
  the session audit trail; cross-cloud calls are not automatically captured by
  either cloud's audit system; instrument explicitly
- Data residency requirements apply to GCP runners too — a GCP runner in
  `europe-west1` that routes inference to Bedrock `us-east-1` may violate the
  same EU data residency constraints as an AWS runner doing the same; evaluate
  cross-cloud inference routing against the data jurisdiction policy before deploying

## Stack Options

**GCP runner runtime**
- Cloud Run (recommended) — `gcloud run deploy coding-agent-runner --image
  gcr.io/platform/agent-harness:latest --region europe-west1 --service-account
  agent-runner@project.iam.gserviceaccount.com --vpc-connector platform-vpc`;
  CPU always-on (`--no-cpu-throttling`) for low-latency tool responses; min
  instances 1 per active BU to avoid cold starts; max instances set to session
  concurrency limit
- GKE Autopilot — for organizations preferring Kubernetes management model without
  manual node pool management; Workload Identity bound at pod spec level;
  `serviceAccountName` in the pod spec maps to a GCP IAM service account;
  horizontal pod autoscaling on session queue depth

**Workload Identity Federation**
- Cloud Run native WIF — no configuration required beyond binding the Cloud Run
  service account to GCP IAM roles; the metadata server provides tokens automatically
- GCP Workload Identity Federation from AWS — configure a Workload Identity Pool
  with AWS as the provider; map `google.subject` to the AWS role ARN; the runner
  exchanges its AWS STS token for a GCP access token; no static credentials at
  any point; `gcloud iam workload-identity-pools providers create-aws` to configure

**Cross-cloud model inference**
- Bedrock cross-region inference via HTTPS — Cloud Run service calls Bedrock HTTPS
  endpoint; authenticate via AWS access key stored in GCP Secret Manager (fetched
  at startup, stored in memory only); or configure GCP Workload Identity Federation
  from AWS so no static credentials are needed even for the Bedrock call
- Vertex AI Gemini — `google-cloud-aiplatform` Python SDK; no cross-cloud hop;
  authentication via metadata server (service account); `aiplatform.gapic.PredictionServiceClient`
  with model endpoint `projects/{project}/locations/{region}/publishers/google/models/gemini-pro`

**GCP resource MCP tools**
- Cloud Build MCP tool — wraps `google-cloud-build` Python client; exposes
  `list_builds`, `get_build`, `get_build_log` as MCP tools; service account bound
  to `roles/cloudbuild.builds.viewer`
- GCS MCP tool — wraps `google-cloud-storage` Python client; exposes `read_object`,
  `list_objects`; bound to `roles/storage.objectViewer` on specific buckets only

**Observability and audit**
- Cloud Logging structured logging — `google-cloud-logging` Python client writes
  structured JSON log entries; `LogEntry.json_payload` carries session event fields;
  log name `projects/{project}/logs/coding-agent-sessions`
- Cloud Log Router to Security Lake — Log Router sink exports matching log entries
  to an S3 bucket in the platform's AWS account (cross-cloud sink); entries are
  OCSF-normalized by a Lambda triggered on S3 PutObject; unified in Security Lake
  with AWS runner logs

## Connects to

- [On-Premises Runner](on-prem-runner.md) — the GCP runner and on-prem runner
  share the same OPA bundle consumption pattern and instance registry protocol;
  the governance model treats all non-AWS runners (GCP, Azure, on-prem) as
  registered instances of the federated platform
- [Federation Governance](../ops/federation.md) — GCP runner instances are
  registered in the DynamoDB instance registry and participate in drift detection;
  the OPA bundle server (S3 + CloudFront) serves policy to GCP runners exactly
  as to AWS runners
- [Data Jurisdiction](../access/data-jurisdiction.md) — GCP runner region selection
  must be evaluated against the same data residency requirements as AWS runner
  region selection; EU GCP runners routing to US Bedrock inference may require
  SCC (Standard Contractual Clauses) analysis identical to AWS EU → US inference
- [JupyterLab Surface](../surfaces/jupyterlab.md) — GCP-based JupyterHub (on GKE)
  uses the GCP runner as the execution backend; the Jupyter MCP server sidecar
  runs alongside the GKE notebook pod; Workload Identity provides GCS and BigQuery
  access for the notebook environment
- [Vault Integration](../gateway/vault-integration.md) — for enterprises using
  Vault as PAM on GCP, the vault-credential-broker can run as a Cloud Run service
  using AppRole auth (GCP has no native Vault auth method equivalent to AWS IAM
  auth); alternatively, use GCP Secret Manager as the credential store for
  GCP-scoped tools

## Sources

- [Cloud Run documentation](https://cloud.google.com/run/docs) — to verify on first use — service configuration, VPC connector, minimum instances, Workload Identity
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) — to verify on first use — pool and provider configuration; AWS provider setup; token exchange
- [GCP Workload Identity for Cloud Run](https://cloud.google.com/run/docs/securing/service-identity) — to verify on first use — service account binding; metadata server token access
- [Cloud Logging structured logging (Python)](https://cloud.google.com/logging/docs/setup/python) — to verify on first use — LogEntry JSON payload; log name; severity
- [Cloud Log Router sinks](https://cloud.google.com/logging/docs/export/configure_export_v2) — to verify on first use — cross-cloud S3 sink configuration
