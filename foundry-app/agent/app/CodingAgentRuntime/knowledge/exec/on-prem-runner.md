---
type: platform-component
title: On-Premises & Hybrid Execution
description: running agent execution on-premises or in an air-gapped environment — for hardware-in-the-loop test infrastructure, classified labs, or regulatory environments where cloud compute cannot be used
group: exec
tags: [exec, on-premises, hybrid, air-gapped, hardware-in-the-loop, hil, embedded, classified, self-hosted, runner]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [on-premises, on-prem, air-gapped, hardware-in-the-loop, hil, classified-lab, local-runner, hybrid-execution, embedded-test, hardware-test, no-cloud-compute, self-hosted-runner]
decision-question: "Do any developer workflows require agent execution on local or air-gapped infrastructure — because the agent needs physical hardware access, the environment cannot reach the internet, or regulatory requirements prohibit cloud compute for that workload?"
---

Most coding agent execution runs comfortably in cloud compute. But some developer
workflows are irreducibly local:

- **Hardware-in-the-loop (HIL) testing** — the agent invokes a test that requires
  a physical hardware target (an FPGA board, a microcontroller, an automotive ECU);
  the test infrastructure cannot be in the cloud because the hardware is on-premises
- **Air-gapped classified environments** — the development network has no internet
  egress by design; cloud compute is not an option; the entire platform must run locally
- **Embedded firmware build pipelines** — proprietary toolchains (chip vendor IDEs,
  JTAG debuggers, license servers) cannot be containerized or cloud-hosted due to
  vendor licensing or hardware dongle requirements
- **On-premises data residency** — regulatory or contractual requirements that
  prohibit source code from leaving the corporate datacenter; cloud inference is
  prohibited even on a private endpoint

The on-premises runner is the execution tier for these cases. It runs agent logic
locally while optionally connecting to cloud services (model inference, secrets
management, observability) over a controlled egress path — or operating entirely
air-gapped with local substitutes for every cloud dependency.

## Architecture Patterns

### Hybrid: Local execution + cloud inference

```
Developer IDE
    └── Agent process (Strands/LangChain, local runner)
          ├── File system tools (local)
          ├── Build/test tools (local hardware toolchain, HIL test harness)
          ├── Model inference → Bedrock (via controlled egress, e.g., AWS Direct Connect or VPN)
          └── Secrets → Secrets Manager (same controlled egress)
```

The agent runs locally; inference calls leave the corporate network via a controlled,
audited egress path. This satisfies hardware-access requirements without requiring
a fully air-gapped model.

### Fully air-gapped: Everything local

```
Developer workstation / lab server
    └── Agent process (Strands/LangChain, local runner)
          ├── File system tools (local)
          ├── Build/test tools (local)
          ├── Model inference → self-hosted LLM (Ollama, vLLM, LM Studio)
          └── Secrets → Vault (on-premises) or local config file (dev only)
```

No cloud dependencies. Fully self-contained. Highest ops burden. Required for
classified environments or when internet egress is prohibited.

## Decisions

**Which execution model applies?**
- Hybrid (local execution + cloud inference) — agent runs on developer workstation
  or lab server; inference calls go to Bedrock over VPN or Direct Connect; suitable
  for HIL environments where the network has controlled internet egress; keeps
  inference quality high while satisfying hardware-access requirements
- Fully air-gapped — no internet egress; self-hosted model required; suitable for
  classified labs or environments with strict data residency requirements
- Hybrid with local inference fallback — standard mode is cloud inference over
  controlled egress; when the network is unavailable (e.g., lab is offline),
  the agent falls back to a locally-hosted smaller model; graceful degradation
  rather than complete outage

**What is the self-hosted model for the air-gapped case?**
- Ollama — lightweight local model server; runs open-weight models (Llama 3,
  Mistral, CodeLlama, Qwen, DeepSeek Coder) on developer hardware (Apple Silicon,
  NVIDIA GPU); zero-config setup; REST API compatible with OpenAI format; good
  for development and low-concurrency lab environments
- vLLM — production-grade serving framework; GPU-optimized; supports continuous
  batching for multi-developer shared inference servers; higher setup complexity
  than Ollama; recommended for shared lab servers serving multiple developers
- AWS Neuron on EC2 Inf2/Trn1 (for hybrid on-prem + private cloud) — if the
  organization has private AWS Direct Connect and uses AWS Outposts, run model
  inference on Inf2 instances within the corporate network boundary; Bedrock is
  not available on Outposts, so Neuron SDK + self-hosted model is required
- LM Studio — desktop application for local model inference; developer-friendly;
  suitable for individual developer workstations; not suitable for shared lab servers

**How is the local runner integrated with the platform's identity and policy model?**
- Local runner registers with the central MCP gateway — the runner authenticates
  to the MCP gateway over the controlled egress path; tool calls are still routed
  through the gateway (enforcing allowlists and logging); model inference is the
  only component that runs locally; this minimizes divergence from the standard
  platform architecture
- Fully local runner with local OPA policy enforcement — in the air-gapped case,
  the OPA policy bundle is pre-loaded from the last bundle sync; the runner enforces
  policies locally without connecting to the bundle server; bundle updates require
  a manual sync when the network is available (or a physically-delivered update)

**How are secrets managed in the air-gapped case?**
- HashiCorp Vault (self-hosted) — on-premises Vault instance; stores API keys,
  SCM tokens, and any other secrets the agent needs; Vault is the industry standard
  for on-premises secret management; supports offline operation; Vault Enterprise
  has disaster recovery clustering for high availability
- AWS Secrets Manager via Direct Connect — for hybrid environments with Direct Connect;
  the agent fetches secrets from Secrets Manager over the private network path;
  no secrets stored locally; preferred when the network path is reliable
- Encrypted local config (development only) — acceptable for individual developer
  workstations during initial setup; never in shared lab environments; secrets
  encrypted with developer's key; rotation is manual

**How is the on-premises runner monitored?**
- Local log forwarding over controlled egress — the runner forwards audit logs to
  the central SIEM over the same controlled egress path used for model inference;
  maintains unified audit trail without requiring the SIEM to be on-premises
- Local log buffer with batch upload — logs are buffered locally and uploaded when
  the egress path is available (tolerates intermittent connectivity); upload
  cadence and buffer size are configurable; ensures no log loss during network
  interruptions
- Air-gapped: local log store only — logs written to a local immutable store
  (append-only file or local S3-compatible store like MinIO); physically transferred
  to the central SIEM via approved media or a secure data diode

**How is the runner software updated in the air-gapped case?**
- Offline update package — the platform team prepares signed update packages
  (container images, policy bundles, model weights) for distribution to air-gapped
  environments; packages are signed with the platform's code signing key; runner
  validates signature before applying; update applied via a controlled change
  management process in the classified environment

## Principles

- The on-premises runner is not a special case — it is a first-class execution
  tier; the same OPA policies, the same tool allowlists, and the same audit
  requirements apply; the execution location differs, not the governance standard
- Prefer hybrid over fully air-gapped where possible — hybrid preserves access
  to frontier model capability and eliminates the self-hosted model ops burden;
  use air-gapped only when the network boundary is a hard requirement
- Local inference is a capability tradeoff — self-hosted models (Llama 3 70B,
  CodeLlama 34B, DeepSeek Coder 33B) are significantly less capable than frontier
  models for complex tasks; set developer expectations appropriately; use the
  model capability evaluation framework (model-capability-eval.md) to baseline
  the specific self-hosted model against the domain's tasks
- Secret management is never local config in a shared environment — a shared lab
  server with credentials in a local config file is a credential exfiltration risk;
  Vault or Secrets Manager is required for any shared environment
- Hardware-in-the-loop test integration is the agent's responsibility, not the
  runner's — the runner provides local execution; the agent code is responsible
  for discovering and invoking the HIL test harness tools; document the MCP tool
  interface for HIL test invocation so that agent code is portable across lab setups

## Stack Options

**Local runner execution**
- Strands Agents (Python) running locally — install Strands in a Python virtual
  environment on the developer workstation or lab server; configure Bedrock endpoint
  (cloud) or local model endpoint (air-gapped); Strands tool definitions invoke
  local build system commands, JTAG debuggers, test harnesses; no container
  required for developer workstation use
- Docker container on local host — package the agent process as a container;
  run with `--network host` (for HIL device access) or a custom bridge network;
  volume-mount the source code directory; suitable for lab servers where consistent
  environment is important

**Self-hosted model inference**
- Ollama — `curl` installable; supports Llama 3 (8B/70B), Mistral, CodeLlama,
  Qwen 2.5 Coder, DeepSeek Coder; REST API on `localhost:11434`; compatible with
  OpenAI API format; configure LiteLLM to point to Ollama endpoint for transparent
  model switching; best for individual developer workstations
- vLLM — `pip install vllm`; serves OpenAI-compatible API on configured port;
  continuous batching for multi-user throughput; supports FP8 quantization for
  smaller GPU footprint; recommended for shared lab servers with NVIDIA GPUs
- Hugging Face Text Generation Inference (TGI) — Docker-based; optimized for
  Transformer models; supports GPTQ/AWQ quantized models for smaller hardware;
  alternative to vLLM for shared server deployment

**Secrets management (on-premises)**
- HashiCorp Vault OSS — open-source edition; runs as a single binary; file
  storage backend for development, Raft storage for production HA; AppRole auth
  for agent process authentication; dynamic secrets for SCM tokens
- AWS Secrets Manager via Direct Connect — preferred for hybrid environments;
  agent process authenticates to Secrets Manager using an IAM role credential
  delivered via EC2 instance metadata or Direct Connect-accessible IMDS; no
  local secret storage

**Log management (air-gapped)**
- MinIO (S3-compatible local store) — deploy MinIO on the lab server; configure
  the agent's CloudWatch SDK equivalent to write to MinIO endpoint; logs persist
  locally; MinIO bucket versioning prevents log tampering; logs transferred to
  central SIEM via approved process
- Fluentd / Fluent Bit with local buffer — lightweight log forwarder that buffers
  locally and forwards to central destination when connectivity is available;
  configurable retry and buffer size; suitable for intermittent-connectivity
  hybrid environments

**OPA policy (air-gapped)**
- Pre-loaded OPA bundle — package the latest signed OPA bundle into the runner
  container image or update package; OPA runs in standalone mode without external
  bundle server; policy version is fixed to the bundle version in the package;
  a policy update requires a new runner deployment package

## Connects to

- [Local Execution](local.md) — on-prem runner is an extension of local execution
  for the hybrid case; the base local execution model applies; this node adds
  the HIL integration, air-gapped, and shared-lab-server dimensions
- [Model Tiering](../gateway/model-tiering.md) — self-hosted models in the air-gapped
  case change the tier economics; a locally-hosted Llama 70B is T2-class capability
  at T1-class latency on good hardware; recalibrate tier assignments for the
  local model's actual capability
- [Model Capability Evaluation](../quality/model-capability-eval.md) — always
  run a capability evaluation on the self-hosted model for domain-specific code
  before deploying to developers; local models have different capability profiles
  than frontier models
- [Observability & Audit](../ops/observability.md) — on-premises runners are
  a distinct log source; the observability pipeline must have an ingestion path
  for runners that cannot send logs in real time (buffered upload, media transfer)
- [Security Posture](../access/security-posture.md) — local runners running on
  developer workstations have a larger attack surface than cloud-hosted containers;
  prompt injection via the local file system is a distinct threat vector; local
  OPA policy enforcement is the compensating control

## Sources

- [Ollama](https://ollama.com/docs) — to verify on first use — local model server; supported models; REST API
- [vLLM documentation](https://docs.vllm.ai/) — to verify on first use — production GPU inference server; OpenAI-compatible API; continuous batching
- [HashiCorp Vault OSS](https://developer.hashicorp.com/vault/docs) — to verify on first use — on-premises secret management; AppRole auth; Raft HA storage
- [Strands Agents — local execution](https://strandsagents.com/latest/) — to verify on first use — local Python execution; custom tool integration; model endpoint configuration
- [AWS Outposts — supported services](https://docs.aws.amazon.com/outposts/latest/userguide/what-is-outposts.html) — to verify on first use — Bedrock availability on Outposts (verify current status before designing hybrid architecture)
