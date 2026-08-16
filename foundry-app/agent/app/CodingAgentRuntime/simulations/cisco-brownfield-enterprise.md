# Simulation: Cisco Systems — Brownfield Enterprise (Re-simulation)

> **Note:** This is a re-simulation of the original Cisco scenario, now drawing on a significantly expanded OKF (57 nodes vs 32 in the original). The comparison section at the end documents what improved and what new gaps were surfaced.

---

## Customer Profile

| Attribute | Value |
|---|---|
| Company | Cisco Systems — global networking and enterprise technology |
| Developers | ~20,000 globally |
| Products | IOS/NX-OS networking OS, Webex, Meraki, ThousandEyes, Duo Security, Umbrella, Secure Firewall, Silicon One ASICs |
| Engineering centers | US (San Jose HQ), India, Israel, UK, Poland, China (R&D) |
| Code domains | C (IOS/NX-OS), C++ (networking stack), Python (automation), Java (enterprise apps), Go (cloud-native), Verilog/SystemVerilog (Silicon One), Embedded C (hardware firmware), Assembly (bootloader/crypto routines) |
| IDEs | VS Code, JetBrains (IntelliJ, CLion) |
| CI/CD | Jenkins (~40%), GitHub Actions (~40%), internal Cisco CI (~20%) |
| SCM | GitHub Enterprise |
| Identity | 11 IdPs: corporate Okta, Azure Entra (BroadSoft acquisition), Duo (own product), several legacy AD forests, China IdP, Israel BU Azure Entra |
| Secrets | HashiCorp Vault (enterprise standard) |

---

## Advisor Discovery

**Advisor:** Cisco builds networking hardware and software for the US government and defense sector. Before we design anything — do any of your repos contain technical data that might be ITAR-controlled? Firmware for military communications equipment, certain encryption implementations, anything on the US Munitions List?

**Customer (Platform Architecture Lead):** Some IOS XE variants and certain firmware for government-contract hardware likely qualify. We've never formally assessed it for ITAR. We also have assembly code for hardware-accelerated cryptographic routines — those might be EAR-controlled.

**Advisor:** The ITAR question needs a written determination from your export control counsel before we design access to those repos. I'll flag that as an escalation. The crypto assembly is almost certainly EAR-controlled under ECCN 5D002 — encryption source code. EAR doesn't require GovCloud like ITAR does, but it does require access controls and audit trail. Are your developers who work on that assembly all US persons, or international?

**Customer:** Mix. We have engineers in India and Israel who work on some of that code.

**Advisor:** For EAR 5D002, you need to assess whether those international engineers' access constitutes a deemed export requiring a license. Again — counsel determination, not platform team determination. The platform can enforce access controls once you have the classification; it can't make the classification itself. Let's assume for design purposes that ITAR repos get a GovCloud instance and EAR repos get enhanced access controls with US-person preference. Now — your 11 IdPs. Walk me through them.

**Customer:** Corporate Okta is the main one. Then we have Azure Entra from the BroadSoft acquisition, Duo which is our own product that some teams use for SSO, two or three legacy AD forests from earlier acquisitions, a separate China IdP, and the Israel BU has their own Azure Entra because they were acquired more recently.

**Advisor:** The broker pattern is the only manageable solution here. You need an orchestrator — Okta, since it's already your corporate standard — that accepts federation from all non-China upstream sources and issues normalized tokens to the platform. The platform trusts one issuer: Okta. The key work is claim normalization — mapping `country`, `employeeType`, `department` from 11 different schemas to a consistent set. The US-person attribute for the ITAR gate must flow reliably through this chain. The China IdP cannot connect to the global broker — Chinese PIPL prohibits sending Chinese developers' personal data outside China through the broker. China gets a separate isolated instance.

**Customer:** We're in active patent litigation over networking protocol stack code. Legal hold covers three repositories in the IOS XE codebase.

**Advisor:** Those three repos need: hard write blocking at the registry level — agent physically cannot write to them; e-discovery-grade session logging routed to a separate WORM bucket (S3 Object Lock COMPLIANCE mode) with cryptographic chain-of-custody; indefinite retention until legal counsel releases the hold; and legal team notification on every AI session that touches these repos. Standard audit logs are not sufficient for e-discovery. The write block must be a hard permission denial, not a guardrail configuration.

**Customer:** Our Silicon One team writes SystemVerilog for custom networking ASICs. They're very excited about AI assistance. But have frontier models actually been evaluated for SystemVerilog?

**Advisor:** No public evaluation exists specifically for production SystemVerilog at ASIC complexity. This is a domain where we genuinely don't know. I'd strongly recommend a model capability evaluation before deploying to Silicon One — define tasks (completion, bug explanation, testbench generation, timing constraint review), build an evaluation dataset from real SystemVerilog, define pass criteria before running, segment results by task type, make a go/no-go per task. There's also an IP concern: unreleased ASIC designs are Cisco's most sensitive IP. DLP rules for Silicon One repos must treat chip architecture details as top-tier confidential.

**Customer:** Poland — we have about 800 engineers there. Any compliance issues?

**Advisor:** Polish labor law has employee monitoring co-determination requirements. Same design principle as Germany: team-level attribution only in management-facing tools; no per-developer performance metrics; individual data accessible only to the developer themselves. Engage employment law counsel in Poland before deploying. I'd recommend designing for this from the start globally — no per-developer metrics anywhere — rather than having a per-country exception model.

**Customer:** Our secrets management is HashiCorp Vault. Will the MCP gateway work with Vault?

**Advisor:** Not natively. The standard AgentCore Gateway integrates with AWS Secrets Manager and IAM role injection. Vault requires a custom adapter — a Lambda that authenticates to Vault using the developer's IAM session token (Vault AWS IAM auth method), fetches the required secret, and injects it into the MCP tool context. It's a 1-2 sprint platform engineering task. I'll flag this as a gap in the knowledge base — Vault integration deserves a dedicated node given how common it is at enterprise scale.

**Customer:** We have some developers in air-gapped environments for nuclear power plant control system work — maybe 50 people.

**Advisor:** Air-gapped means no cloud inference. Options: (1) exclude this population — their workflows are unusual enough to warrant a separate approach; (2) on-premises runner with a self-hosted model (Ollama with CodeLlama 70B or Llama 3 70B on GPU lab servers). Option 2 is fully offline — no internet required. Capability is lower than frontier models, but for code explanation and review it's workable. OPA policy bundle is pre-loaded and updated during scheduled maintenance windows with a signed bundle package delivered via approved media.

**Customer:** The Israel BU — they were acquired and run entirely on Azure. No AWS migration is funded.

**Advisor:** Treat them as a permanent multi-cloud spoke. Deploy Strands Agents on Azure Container Apps, federated to the central identity broker via their existing Azure Entra (already federated to Okta). OPA policy bundles pulled from the central S3 bundle server. Azure OpenAI Service for inference — keeps inference within Azure boundary. Azure Monitor → Event Hub → Splunk for the observability pipeline. Governance parity without requiring a migration.

**Customer:** What does the cost model look like at 20,000 developers?

**Advisor:** With model tiering — Haiku for autocomplete (70% of tokens), Sonnet for single-file edits (25%), Opus for complex multi-file tasks (5%) — and assuming 40% of developers active on any given day: rough estimate is $30–70 per developer per month, or $600K–$1.4M/month at full adoption. Year 1 will be lower due to adoption ramp. I'd model $500K/month for the budget ask, $800K as ceiling. Per-BU monthly quotas and per-session cost ceilings keep you from surprises. China instance is separate cost on Alibaba pricing.

---

## Platform Blueprint

### Instance Topology

```
Central Platform Team (San Jose)
├── Policy Canon: OPA bundle server (S3 + CloudFront, signed bundles)
├── Identity Broker: Okta Workforce Identity Cloud (orchestrator)
│   ├── Corporate Okta → pass-through
│   ├── BroadSoft Azure Entra → SAML federation into Okta
│   ├── Duo → OIDC federation into Okta
│   ├── AD Forest 1, 2, 3 → LDAP sync + SAML into Okta
│   ├── Israel Azure Entra → SAML federation into Okta
│   └── [China IdP — NOT connected; isolated by PIPL]
│   Okta → AWS IAM Identity Center (SAML external IdP)
├── Vault Adapter: Lambda `vault-credential-broker` (AWS IAM auth method)
└── Central SIEM: Splunk (all non-China, non-GovCloud instances)

Instance 1: Global Commercial (us-east-1) — PRIMARY
  Populations: Java, Python, Go, TypeScript, C++ (non-ITAR), IOS/NX-OS C (read-only)
  Harness: Claude Code Enterprise
  MCP Gateway: AgentCore Gateway + Vault adapter
  Model: Bedrock (Haiku/Sonnet/Opus tiered) via VPC endpoint
  Legal hold: write-blocked repos; WORM session log stream (S3 Object Lock COMPLIANCE)

Instance 2: ITAR GovCloud (us-gov-east-1)
  Population: ITAR-classified firmware/HDL engineers (~200, US persons only)
  Harness: Strands on ECS (verify Claude Code GovCloud availability)
  Policy: Separate OPA bundle server (GovCloud-resident); ITAR rules active
  US-person gate: Lambda authorizer → HR API → usPersonStatus check
  Model: Bedrock GovCloud (verify current model list)
  Access: Central platform team has NO access to this account

Instance 3: Israel BU — Azure governance overlay
  Population: Israel BU (~1,200 engineers)
  Harness: Strands Agents on Azure Container Apps
  Policy: OPA bundle from central S3 bundle server
  Identity: Israel Entra → Okta → global broker
  Model: Azure OpenAI Service (in-Azure inference)
  Observability: Azure Monitor → Event Hub → Splunk

Instance 4: China R&D (AWS China Ningxia)
  Population: China R&D engineers (~600)
  Harness: LangChain on ECS (AWS China)
  Policy: Separate OPA bundle (PIPL-compliant)
  Identity: China IdP only — NO connection to global broker
  Model: Alibaba Tongyi/DashScope via LiteLLM
  Observability: Local CloudWatch only; NOT exported outside China

Instance 5: Air-Gapped Lab (On-premises)
  Population: ~50 engineers (nuclear/critical infrastructure code)
  Harness: Strands Agents (Python) on lab GPU servers
  Policy: Pre-loaded OPA bundle; updated via signed package delivery
  Model: Ollama (CodeLlama 70B) on lab server
  Mode: Read-only — code explanation and review only
```

### Phase 1: Foundation — Global Commercial Instance (Months 1–3)

**Prerequisites (parallel workstreams):**
1. Export control counsel: ITAR boundary determination + EAR 5D002 classification for crypto assembly
2. Legal: e-discovery log specification for three IOS XE litigation hold repos
3. Vault adapter: 1-2 sprint Lambda build (AWS IAM auth method → Vault → credential injection)
4. Poland employment law: counsel assessment of co-determination obligations
5. Silicon One capability eval: begin SystemVerilog evaluation dataset construction

**Identity federation:**
- Configure 7 upstream IdPs into Okta (corporate Okta pass-through + 6 external)
- Claim normalization rules in Okta Expression Language: `country_iso`, `business_unit`, `employment_type`, `us_person`
- US-person attribute: sourced from Cisco HR API, not self-certified
- Okta → IAM Identity Center SAML federation
- Permission sets: `cisco-standard-developer`, `cisco-itar-readonly`, `cisco-platform-admin`
- MFA: enforce at Okta level; inherited through SAML assertion

**Legal hold activation:**
- Three IOS XE repos tagged `legal-hold` in GitHub Enterprise; SSM Parameter Store holds registry
- Session init Lambda: check registry; if repo in hold → remove all write tools from allowlist
- E-discovery log bucket: S3 Object Lock COMPLIANCE mode; access restricted to legal custodians only
- Cryptographic log chaining: Lambda appends each session event with hash of previous record
- EventBridge rule: any session touching legal-hold repo → SNS notification to legal team

**IOS/NX-OS networking developers:**
- Read-only mode: C/IOS repos have write tools removed from allowlist
- Agent can explain, document, and review — not edit, commit, or branch
- 6-month trial; write access evaluation at month-6 checkpoint

**Observability (no per-developer metrics):**
- CloudWatch dimensions: `team`, `business_unit`, `language_domain`, `instance_id` — no `developer_id`
- Audit log access: security team only; encrypted with CMK; key policy restricts decryption
- WORM routing: EventBridge routes legal-hold and EAR sessions to WORM bucket; all others to standard bucket

### Phase 2: Specialized Instances + BU Rollout (Months 3–6)

**ITAR GovCloud instance:**
- Counsel determination received (prerequisite)
- US-person roster current in HR system (prerequisite)
- Lambda authorizer checks `usPersonStatus` at every session; ITAR-tagged repos blocked if false
- Separate OPA bundle server within GovCloud account
- San Jose platform team: zero IAM, zero log, zero console access to GovCloud

**Israel Azure overlay:**
- Strands Agents deployed to Azure Container Apps with Managed Identity
- OPA sidecar pulls bundle from central S3 bundle server
- Azure OpenAI as inference; data stays in Azure boundary
- Azure Monitor → Event Hub → Splunk Add-on → central Splunk

**Silicon One rollout:**
- Capability evaluation complete (prerequisite): enable only tasks that passed evaluation thresholds
- DLP: Bedrock Guardrails with custom data identifiers for chip IP (part numbers, process node, unreleased codenames)
- Repo tag `chip-ip-unreleased`: enhanced DLP + metadata-only session logging (no prompt/response content logged)

**EAR 5D002 crypto assembly:**
- Repo tag `ear-eccn-5d002`; session Lambda checks tag
- Compliance log stream: every EAR session generates audit record with US-person status
- WORM retention: 5 years for EAR session logs (confirm retention period with counsel)
- International engineer access: logged for EAR compliance review; counsel determines if license required

### Phase 3: China + Air-Gapped + Full Rollout (Months 6–9)

**China instance:**
- AWS China Ningxia account; separate credentials and console login
- Local China IdP; no Okta connection
- Alibaba DashScope (Tongyi Qianwen) via LiteLLM
- MLPS assessment with AWS China SINNET team
- Local observability only; no export outside China

**Air-gapped lab:**
- GPU lab server provisioned with NVIDIA GPU
- Ollama serving CodeLlama 70B or Llama 3 70B
- Strands agent running locally pointing to Ollama endpoint
- Pre-loaded OPA bundle; signed bundle package for updates
- Read-only mode: write tools not in allowlist
- Capability eval: run eval on nuclear control C code with local model; set expectations

**Cost summary at full rollout:**
| Instance | Developers | Model | Est. $/dev/mo | Monthly |
|---|---|---|---|---|
| Global commercial | 18,500 | Haiku/Sonnet/Opus tiered | $35 | $647,500 |
| GovCloud | 200 | Sonnet/Opus | $55 | $11,000 |
| Israel (Azure) | 1,200 | Azure OpenAI (separate billing) | ~$40 | ~$48,000 |
| China | 600 | Alibaba Tongyi | ~$15 | ~$9,000 |
| Air-gapped | 50 | Self-hosted (hardware capex) | ~$0 | ~$0 |
| **Total** | **20,550** | | | **~$715,500/mo** |

Budget ask: $800K/month ceiling; ~$500K expected in Year 1 ramp.

### Key Tradeoffs Accepted

| Decision | Choice | Rationale |
|---|---|---|
| IOS/NX-OS repos | Read-only 6-month trial | Team requested; networking OS invariants need validation before write access |
| Vault adapter | Custom Lambda build (1-2 sprints) | Enterprise secrets standard is non-negotiable |
| China | Alibaba Tongyi, fully isolated | PIPL + Bedrock unavailability forces isolation |
| Israel BU | Azure Container Apps + OSS | No migration required; governance via OPA |
| Air-gapped | Ollama read-only | Cloud inference impossible; local model for explanation workload |
| No per-developer metrics | Global policy | Poland works council + global consistency; legal risk mitigation |
| Silicon One | Capability eval first, task-scoped deployment | Production SystemVerilog eval required before committing |

### Escalations to Legal / Compliance

1. **Export control counsel:** ITAR boundary (Bedrock GovCloud vs commercial); EAR 5D002 classification for crypto assembly; deemed export analysis for international engineers on EAR repos
2. **Legal hold:** E-discovery log specification; retention period; release procedure
3. **Employment law — Poland:** Co-determination obligations for AI monitoring systems
4. **Privacy counsel:** PIPL assessment for China; UK/EU GDPR data processor agreements
5. **MLPS:** China instance MLPS level determination with AWS China SINNET

### Platform Best Practices

- **Resilience:** Adaptive retry on all Bedrock calls; circuit-breaker per MCP server; Vault adapter gracefully degrades if Vault unreachable (session continues without external tool credentials)
- **Credential hygiene:** Vault adapter issues ephemeral credentials per session; no standing credentials anywhere; truffleHog on all platform repos
- **Change safety:** Auto-branch on all sessions; no direct main commits; idle timeout 30 minutes
- **Policy canon integrity:** OPA bundles signed; instances reject unsigned bundles; bundle version reported to instance registry every 60 seconds
- **Legal hold chain:** Cryptographic log chain verified weekly by scheduled Lambda; any gap or modification alerts legal team immediately

### Org Readiness Flags

| Dimension | What's needed | Owner |
|---|---|---|
| Export control process | ITAR/EAR repo classification workflow; reclassification process as repos change | Export Control Officer |
| Legal hold procedure | Written procedure: how holds are placed and released; platform team acts on written counsel instruction only | Legal + Platform team |
| Silicon One eval | 2 senior SystemVerilog engineers as evaluators; 4-week timeline | Silicon One engineering lead |
| Vault adapter | 1-2 sprint build | Platform Engineering |
| IOS/NX-OS month-6 review | Read-only trial results → write access decision | Networking OS lead + CTO |
| China operations | China-resident platform admin; PIPL data controller designation | China R&D leadership |
| Cost governance | BU quota allocation; monthly cost review; escalation for quota increases | Finance + Platform team |

---

## Post-Simulation Advisor Notes

### What the Advisor Handled Well (vs Original Simulation)

The original simulation surfaced 9 OKF gaps. All 9 are now covered by dedicated nodes:

| Original Gap | Now Covered By |
|---|---|
| Export control (ITAR/EAR) | `access/export-control.md` — full framework, US-person check, GovCloud boundary |
| Data jurisdiction (China PIPL/MLPS) | `access/data-jurisdiction.md` — isolation pattern, Chinese LLM providers, SCP enforcement |
| IdP federation (11 IdPs) | `access/idp-federation.md` — broker pattern, claim normalization, acquisition runbook |
| HR system integration | `access/idp-federation.md` — HR API for us_person claim at session init |
| Legal hold | `access/legal-hold.md` — WORM, write blocking, cryptographic chain, EventBridge notification |
| Model capability evaluation | `quality/model-capability-eval.md` — 6-step framework, HDL-specific guidance |
| On-prem runner | `exec/on-prem-runner.md` — Ollama/vLLM, pre-loaded OPA, air-gapped patterns |
| Multi-cloud governance | `ops/multi-cloud-governance.md` — OPA canon, Azure Container Apps overlay |
| Works council / regional compliance | `access/regional-compliance.md` — attribution model, Betriebsvereinbarung, GDPR |

The re-simulation is substantially more concrete in each area. Specific stack choices (Ollama for air-gap, Alibaba DashScope for China, Azure OpenAI for Israel) are now provided rather than flagged as unknowns.

### New Issues Surfaced (Not in Original)

**HashiCorp Vault integration** — Surfaced and partially addressed but no OKF node exists. Vault is the enterprise secrets standard at many large organizations beyond Cisco. High-priority gap.

**EAR 5D002 nuance** — The export-control node covers EAR generally but doesn't detail ECCN 5D002 encryption source code specifically, the deemed export analysis for international engineers, or the audit trail requirements that differ from ITAR (no GovCloud requirement but still enhanced controls needed).

**Custom CI system** — 20% of Cisco's CI is a proprietary internal platform. The CI surface node covers GitHub Actions and standard tools but not integration patterns for custom/proprietary build systems.

**Cost attribution without per-developer metrics** — How to do accurate BU cost attribution when `developer_id` dimension is forbidden. The answer (CMK-encrypted session records, BU-level metric aggregation) is implied but not explicit in any current node.

### OKF Gaps Identified

| Gap Name | Description | Priority | Trigger Signals |
|---|---|---|---|
| `gateway/vault-integration.md` | HashiCorp Vault MCP gateway adapter — AWS IAM auth method, AppRole, dynamic secrets, token refresh, graceful degradation | High | hashicorp-vault, vault, enterprise-secrets, no-secrets-manager, pam |
| Extend `access/export-control.md` | EAR 5D002 encryption source code — deemed export analysis, international engineer access controls, audit trail (non-GovCloud), EAR license exception criteria | High | ear-5d002, eccn, encryption-source-code, deemed-export, crypto-routines |
| `surfaces/custom-ci.md` | Custom/proprietary CI integration — MCP tool patterns for non-standard CI systems, make-based pipelines, Cisco-style internal build platforms | Medium | custom-ci, internal-ci, proprietary-build, make |
| `ops/cost-attribution-privacy.md` | BU-level cost attribution in privacy-constrained environments — CMK-encrypted individual records, BU aggregation without dev-level exposure, quota allocation methodology | Medium | works-council-cost, no-dev-metrics, bу-cost-attribution |
| `exec/gcp-runner.md` | GCP-native OSS framework deployment — Cloud Run, Workload Identity Federation, GCP observability to central SIEM | Medium | gcp, google-cloud, cloud-run, gcp-acquisition |

### Comparison with Original Simulation

| Dimension | Original | Re-simulation |
|---|---|---|
| ITAR handling | Gap flagged | Full GovCloud instance; US-person gate; counsel escalation structured |
| China | Gap flagged | Specific stack: Alibaba DashScope + PIPL isolation + MLPS flagged |
| Legal hold | Gap flagged | WORM + crypto chain + write-block + EventBridge notification |
| 11 IdPs | Gap flagged | Okta orchestrator + claim normalization schema + China isolation |
| SystemVerilog | Gap flagged | 6-step capability eval + IP DLP configuration |
| Air-gapped | Gap flagged | Ollama on lab server + pre-loaded OPA + signed bundle delivery |
| Works council (Poland) | Not surfaced | Proactively surfaced; team-level metrics recommendation |
| Vault | Not surfaced | Surfaced and partially addressed; gap node recommended |
| EAR 5D002 | Not surfaced | Surfaced; partial guidance; deeper coverage needed |
| Cost model | Not provided | $715K/mo estimate with per-instance breakdown + Year 1 ramp |
| Instance topology | 5 instances named | 5 instances with full specs, models, policy distribution, access controls |
