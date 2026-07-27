# Compliance Overlays: Industry-Specific Platform Modifications

## Purpose

This document defines industry-specific compliance overlays that modify the base agent platform architecture. Each overlay specifies regulatory frameworks, forced component tiers, required additions, and specific AgentCore configurations. Apply these overlays ON TOP of the chosen architecture pattern (Centralized, Federated, or Mesh).

**Audience**: VP of Engineering / VP of Platform in regulated industries, compliance officers, solutions architects.

**Usage by LLM**: When a customer mentions their industry or regulatory requirements, look up the relevant overlay and modify the recommended architecture accordingly. Overlays are additive — they add requirements on top of the base pattern, never remove capabilities.

---

## Overlay 1: Financial Services

### Regulatory Frameworks
- **SOX (Sarbanes-Oxley)** — Internal controls, audit trails, financial reporting integrity
- **PCI-DSS** — Payment card data protection
- **OCC Guidelines (OCC 2011-12)** — Operational risk management for banking
- **SEC/FINRA** — Securities trading compliance, market manipulation prevention
- **GLBA (Gramm-Leach-Bliley)** — Customer financial information protection
- **Basel III/IV** — Risk management and capital requirements
- **FFIEC** — Information security and examination standards

### Forced Component Tiers

| Component | Forced Tier | Rationale |
|-----------|-------------|-----------|
| AgentCore Policy | **Tier 3 (Maximum)** | Automated Reasoning required for any agent producing financial advice or calculations |
| AgentCore Observability | **Tier 3 (Maximum)** | Full audit trails required for all agent decisions — 7-year retention |
| AgentCore Identity | **Tier 3 (Maximum)** | Full delegation chains, audit of who authorized what, non-repudiation |
| AgentCore Evaluations | **Tier 2+** | Continuous production evaluation for accuracy of financial information |
| AgentCore Registry | **Tier 2 (Mandatory)** | Complete inventory of all agents handling financial data |
| AgentCore Memory | **Tier 2 (with controls)** | Must implement data retention policies, purge on request |

### Required Additions

1. **Immutable Audit Log** — Every agent decision stored in append-only format for 7 years minimum
   - AWS: S3 Object Lock (Compliance mode) + Glacier Deep Archive
   - Every LLM call: input, output, model version, timestamp, user context

2. **Data Classification Engine** — Agents must classify data they process (public, internal, confidential, restricted)
   - AgentCore Policy rules tied to data classification
   - Agents cannot promote data classification downward

3. **Segregation of Duties** — Agents that recommend cannot also execute (no agent both suggests a trade AND executes it)
   - Step Functions with separate agent roles for recommend vs. execute
   - Human approval gate between recommendation and execution

4. **Model Risk Management (SR 11-7)** — Agents are "models" under Fed guidance
   - Model validation before production (AgentCore Evaluations)
   - Ongoing performance monitoring (AgentCore Observability)
   - Annual model review documentation

5. **Regulator Explainability** — Must be able to explain any agent decision to regulators
   - AgentCore Observability full traces + AgentCore Policy Automated Reasoning proofs
   - Decision replay capability (reproduce any past decision)

6. **PCI Isolation** — Agents handling card data must run in PCI-scoped environments
   - Separate AgentCore Runtime instances for PCI workloads
   - Network isolation, encryption at rest and in transit
   - No card data in AgentCore Memory or logs (tokenize first)

### Specific AgentCore Configurations

```yaml
# Financial Services Policy Configuration
agentcore_policy:
  automated_reasoning: REQUIRED  # All financial outputs verified
  content_filtering: ENABLED
  pii_detection: STRICT  # Block any PII in responses
  custom_policies:
    - no_investment_advice_without_disclaimer
    - no_forward_looking_statements
    - segregation_of_duties_enforcement
  retention: 7_YEARS

agentcore_observability:
  trace_retention: 7_YEARS
  full_io_logging: REQUIRED
  immutable_storage: S3_OBJECT_LOCK
  export_to: [cloudtrail, splunk, internal_siem]

agentcore_identity:
  delegation_chains: REQUIRED
  non_repudiation: ENABLED
  session_recording: FULL
  mfa_for_high_risk: REQUIRED
```

### Pattern Modification
- **Centralized** preferred for financial services (easier to audit)
- If Federated: central team MUST own compliance enforcement (no LOB override)
- All agents producing financial outputs MUST pass Automated Reasoning checks before delivery
- No autonomous execution for transactions > configurable threshold

---

## Overlay 2: Healthcare

### Regulatory Frameworks
- **HIPAA (Health Insurance Portability and Accountability Act)** — PHI protection
- **HITECH Act** — EHR incentives and breach notification
- **FDA 21 CFR Part 11** — Electronic records and signatures (if clinical decision support)
- **FDA AI/ML SaMD Guidance** — Software as Medical Device considerations
- **HITRUST CSF** — Healthcare information security framework
- **State privacy laws** — Various state-specific health data protections

### Forced Component Tiers

| Component | Forced Tier | Rationale |
|-----------|-------------|-----------|
| AgentCore Policy | **Tier 3 (Maximum)** | PHI boundaries, consent enforcement, Automated Reasoning for clinical accuracy |
| AgentCore Observability | **Tier 3 (Maximum)** | HIPAA audit requirements — who accessed what PHI, when, why |
| AgentCore Identity | **Tier 3 (Maximum)** | Minimum necessary standard enforcement, access controls |
| AgentCore Memory | **Tier 2 (with PHI controls)** | PHI must be encrypted, access-logged, purgeable |
| AgentCore Code Interpreter | **Restricted** | No PHI in sandbox execution environments |
| AgentCore Registry | **Tier 2 (Mandatory)** | Inventory of all agents with PHI access |

### Required Additions

1. **PHI Boundary Controls** — Agents must not transmit PHI outside approved boundaries
   - AgentCore Policy blocks PHI in responses to unauthorized recipients
   - Data Loss Prevention (DLP) integration at AgentCore Gateway level
   - PHI tokenization before any external tool call

2. **Consent Layer** — Agents must verify patient consent before accessing/sharing health data
   - Consent management system integration via AgentCore Gateway
   - Per-patient, per-use-case consent verification
   - Consent status logged in audit trail

3. **Minimum Necessary Standard** — Agents access only the minimum PHI needed for their task
   - AgentCore Identity provides task-scoped credentials (not blanket access)
   - Tool calls via AgentCore Gateway filter to minimum data fields
   - Audit logs verify "need to know" for every PHI access

4. **Clinical Decision Support Guardrails** — If agent provides clinical recommendations
   - Automated Reasoning verification against clinical guidelines
   - Mandatory disclaimers ("This is not medical advice")
   - Physician review requirement before patient communication
   - FDA SaMD classification assessment

5. **Breach Notification Pipeline** — Automated detection and reporting of PHI breaches
   - AgentCore Observability anomaly detection for unauthorized PHI access
   - Automated breach assessment workflow (Step Functions)
   - 60-day notification timeline tracking

6. **De-identification** — Agents working with research data must use de-identified datasets
   - HIPAA Safe Harbor or Expert Determination method compliance
   - AgentCore Policy blocks re-identification attempts

### Specific AgentCore Configurations

```yaml
# Healthcare Policy Configuration
agentcore_policy:
  automated_reasoning: REQUIRED_FOR_CLINICAL  # Clinical outputs verified
  phi_detection: STRICT_BLOCK  # Block any PHI leakage
  consent_verification: REQUIRED
  minimum_necessary: ENFORCED
  custom_policies:
    - no_clinical_advice_without_review
    - phi_boundary_enforcement
    - consent_check_before_access
    - de_identification_for_research

agentcore_memory:
  phi_encryption: AES_256_AT_REST
  access_logging: EVERY_READ
  purge_capability: IMMEDIATE_ON_REQUEST
  retention_policy: PER_STATE_LAW

agentcore_identity:
  minimum_necessary: ENFORCED
  role_based_phi_access: REQUIRED
  break_glass_procedures: CONFIGURED
  access_review_frequency: QUARTERLY

agentcore_observability:
  phi_access_logging: REQUIRED
  breach_detection: ENABLED
  retention: 6_YEARS  # HIPAA requirement
  hipaa_audit_reports: AUTOMATED
```

### Pattern Modification
- **Centralized** strongly preferred for healthcare (single PHI boundary to manage)
- If Federated: central team owns ALL PHI-related controls. LOBs cannot modify PHI policies.
- AgentCore Memory instances containing PHI must be in HIPAA-eligible regions only
- All clinical decision support agents require FDA SaMD classification assessment

---

## Overlay 3: Government

### Regulatory Frameworks
- **FedRAMP** — Federal Risk and Authorization Management Program
- **FISMA** — Federal Information Security Modernization Act
- **NIST 800-53** — Security and privacy controls
- **NIST AI RMF** — AI Risk Management Framework
- **Executive Order 14110** — Safe, Secure, and Trustworthy AI
- **IL4/IL5** — Impact Level classifications for DoD
- **ITAR** — International Traffic in Arms Regulations (defense)
- **Section 508** — Accessibility requirements

### Forced Component Tiers

| Component | Forced Tier | Rationale |
|-----------|-------------|-----------|
| AgentCore Policy | **Tier 3 (Maximum)** | FedRAMP requires continuous monitoring, NIST controls |
| AgentCore Observability | **Tier 3 (Maximum)** | Continuous monitoring mandate, SIEM integration |
| AgentCore Identity | **Tier 3 (Maximum)** | PIV/CAC authentication, zero trust, identity governance |
| AgentCore Runtime | **Tier 2+ (Region-locked)** | Data residency requirements, GovCloud deployment |
| AgentCore Registry | **Tier 2 (Mandatory)** | System inventory requirement (NIST 800-53 CM-8) |
| AgentCore Evaluations | **Tier 2+** | NIST AI RMF compliance requires ongoing testing |

### Required Additions

1. **Data Residency Controls** — Agents and data must remain in approved boundaries
   - GovCloud deployment for IL4+ workloads
   - No cross-region model inference unless approved
   - AgentCore Runtime locked to specific regions
   - Data sovereignty enforcement at AgentCore Gateway level

2. **Boundary Controls** — Network boundaries between classification levels
   - Separate VPCs/accounts per impact level
   - Cross-boundary data transfer requires approval and logging
   - AgentCore Gateway enforces boundary rules for tool calls

3. **Continuous Monitoring (ConMon)** — Ongoing security assessment
   - AgentCore Observability feeds into agency SIEM
   - Automated vulnerability scanning of agent infrastructure
   - Monthly POA&M (Plan of Action & Milestones) generation

4. **AI Risk Management (NIST AI RMF)** — Structured risk assessment for AI systems
   - Map → Measure → Manage → Govern framework applied to each agent
   - Bias testing via AgentCore Evaluations
   - Explainability documentation for each agent
   - Impact assessments before deployment

5. **Authority to Operate (ATO)** — Formal authorization before production use
   - Agent ATO package (system security plan, risk assessment, test results)
   - AgentCore Harness test results as evidence
   - AgentCore Policy configuration as control documentation
   - Continuous ATO maintenance through monitoring

6. **Accessibility (Section 508)** — Agent outputs must be accessible
   - Agents producing documents must meet WCAG 2.1 AA
   - Voice agent alternatives for visual-only outputs
   - Screen reader compatibility for web-based agent interfaces

### Specific AgentCore Configurations

```yaml
# Government Policy Configuration
agentcore_policy:
  automated_reasoning: REQUIRED_FOR_DECISIONS
  content_filtering: STRICT
  data_residency: GOVCLOUD_ONLY  # or specific region lock
  classification_enforcement: ENABLED
  custom_policies:
    - no_cross_boundary_data_transfer
    - cui_marking_required
    - pii_handling_per_privacy_act
    - section_508_compliance

agentcore_runtime:
  region_lock: [us-gov-west-1, us-gov-east-1]  # GovCloud
  fips_140_2: REQUIRED
  encryption_in_transit: TLS_1_3_ONLY

agentcore_identity:
  piv_cac_integration: REQUIRED
  zero_trust: ENFORCED
  privileged_access_management: ENABLED
  identity_governance: CONTINUOUS

agentcore_observability:
  siem_integration: REQUIRED
  continuous_monitoring: ENABLED
  retention: PER_NARA_SCHEDULE
  conmon_reporting: AUTOMATED
  log_encryption: FIPS_140_2
```

### Pattern Modification
- **Centralized** required for most government agencies (ATO boundary management)
- FedRAMP High requires AgentCore deployed in GovCloud (AWS GovCloud regions)
- IL5 workloads require dedicated tenancy
- All agents require ATO documentation — AgentCore Harness + Evaluations provide evidence
- NIST AI RMF compliance documentation required for each agent type

---

## Overlay 4: Retail & E-commerce

### Regulatory Frameworks
- **PCI-DSS** — Payment Card Industry Data Security Standard
- **CCPA/CPRA** — California Consumer Privacy Act
- **GDPR** (if operating in EU) — General Data Protection Regulation
- **FTC Act Section 5** — Unfair or deceptive practices (applies to AI recommendations)
- **CAN-SPAM / TCPA** — Communication consent requirements
- **State consumer protection laws** — Various state-specific requirements

### Forced Component Tiers

| Component | Forced Tier | Rationale |
|-----------|-------------|-----------|
| AgentCore Policy | **Tier 2+** | PCI compliance for payment agents, privacy for customer data |
| AgentCore Identity | **Tier 2+** | Customer identity management, consent-based access |
| AgentCore Observability | **Tier 2** | PCI audit requirements, customer interaction logging |
| AgentCore Memory | **Tier 2 (with controls)** | Customer data retention limits, right to deletion |
| AgentCore Payments | **Tier 2+** | If agents handle commerce transactions |

### Required Additions

1. **PCI Scope Isolation** — Agents handling payment data must be in PCI scope
   - Separate AgentCore Runtime for PCI-scoped agents
   - Tokenize card data before any non-PCI agent interaction
   - Annual PCI-DSS assessment includes agent platform
   - Network segmentation between PCI and non-PCI agents

2. **Customer Data Separation** — Multi-tenant data isolation for marketplace models
   - Agents cannot access cross-customer data
   - AgentCore Memory scoped per customer (no bleed-through)
   - AgentCore Gateway tool calls filter to authorized customer data only
   - Privacy-preserving recommendations (no individual customer data in shared models)

3. **Consent Management** — Track and enforce customer consent for AI interactions
   - Opt-in/opt-out for AI-powered features
   - AgentCore Policy blocks agent action on non-consented customers
   - Consent status checked before personalization
   - Clear disclosure when customers interact with agents (not humans)

4. **Right to Deletion** — CCPA/GDPR compliance for data erasure requests
   - AgentCore Memory must support complete customer data purge
   - Deletion propagates to all agent memory, logs, and derived data
   - Verification that deletion is complete
   - Audit trail of deletion (ironically, must log what was deleted)

5. **Recommendation Fairness** — FTC requirements for non-deceptive recommendations
   - Disclosure when recommendations are AI-generated
   - No deceptive ranking or prioritization
   - AgentCore Evaluations for recommendation bias testing
   - Price discrimination detection

6. **Peak Load Architecture** — Retail agents must handle Black Friday / Prime Day scale
   - AgentCore Runtime auto-scaling with pre-warmed capacity
   - Degradation strategy (reduce agent sophistication under extreme load)
   - Cached responses for common queries during peak
   - Circuit breakers to protect downstream systems

### Specific AgentCore Configurations

```yaml
# Retail/E-commerce Policy Configuration
agentcore_policy:
  pci_isolation: ENFORCED_FOR_PAYMENT_AGENTS
  customer_data_separation: STRICT
  consent_verification: REQUIRED
  recommendation_disclosure: ENABLED
  custom_policies:
    - no_cross_customer_data_access
    - pci_tokenization_required
    - ai_disclosure_in_interactions
    - price_fairness_check

agentcore_memory:
  customer_scoping: PER_CUSTOMER_ISOLATION
  right_to_deletion: SUPPORTED
  retention_limit: PER_PRIVACY_POLICY
  no_cross_customer_bleed: ENFORCED

agentcore_runtime:
  auto_scaling: ENABLED
  peak_capacity_reservation: CONFIGURED
  degradation_strategy: REDUCE_COMPLEXITY
  warm_pools: ENABLED_FOR_PEAK

agentcore_payments:
  transaction_metering: ENABLED
  pci_audit_integration: REQUIRED
  chargeback_tracking: ENABLED
```

### Pattern Modification
- Centralized or Federated both viable for retail
- PCI-scoped agents MUST be in separate runtime instances
- Customer data agents need strict memory isolation (no shared memory pools)
- Peak scaling requires pre-planned capacity — not just auto-scale (which may be too slow)

---

## Overlay 5: Insurance

### Regulatory Frameworks
- **State Insurance Regulations** — Vary by state, governed by state insurance departments
- **NAIC Model Laws** — National Association of Insurance Commissioners guidelines
- **Unfair Trade Practices Act** — Anti-discrimination in insurance
- **Fair Credit Reporting Act (FCRA)** — Credit-based insurance scoring
- **GDPR/CCPA** — Privacy regulations for customer data
- **Solvency II** (EU) — Risk management and capital requirements
- **Colorado AI Act (SB 21-169)** — AI governance for insurance decisions

### Forced Component Tiers

| Component | Forced Tier | Rationale |
|-----------|-------------|-----------|
| AgentCore Policy | **Tier 3 (Maximum)** | Explainability requirements, anti-discrimination, Automated Reasoning |
| AgentCore Observability | **Tier 3 (Maximum)** | Decision audit trails, regulatory examination readiness |
| AgentCore Evaluations | **Tier 3 (Maximum)** | Bias testing, fair lending compliance, ongoing monitoring |
| AgentCore Identity | **Tier 2+** | Policyholder data protection, agent authorization controls |
| AgentCore Registry | **Tier 2 (Mandatory)** | Inventory of all AI models/agents for regulatory filing |

### Required Additions

1. **Explainability Engine** — Every underwriting/claims/pricing decision must be explainable
   - AgentCore Policy Automated Reasoning provides mathematical proof of decision basis
   - Plain-language explanation generation for policyholders
   - Factor attribution (what inputs influenced the decision, and by how much)
   - Adverse action notice generation (why was coverage denied or priced higher?)

2. **Bias Testing & Fair Lending Compliance** — Agents must not discriminate on protected characteristics
   - AgentCore Evaluations with bias-specific test suites
   - Disparate impact analysis on agent decisions (pricing, underwriting, claims)
   - Protected class testing (race, gender, age, disability, etc.)
   - Regular bias audits with documented results for regulators
   - Colorado AI Act compliance: annual impact assessments

3. **Rate Filing Documentation** — AI-influenced pricing must be supportable in rate filings
   - Full documentation of how agents influence pricing decisions
   - Model factor documentation for state regulatory filings
   - Actuarial justification for AI-derived rating factors
   - AgentCore Observability provides decision traces for rate justification

4. **Claims Fairness** — Agents assisting with claims must treat claimants fairly
   - No bias in claims processing speed or outcomes
   - Consistent application of coverage interpretation
   - Escalation to human for borderline/complex claims
   - AgentCore Evaluations monitors claims outcome fairness

5. **Regulatory Examination Readiness** — Must produce documentation for state examiners
   - Complete inventory of all AI/agent systems (AgentCore Registry)
   - Governance documentation (policies, procedures, oversight)
   - Testing and monitoring evidence (AgentCore Evaluations history)
   - Decision audit trails (AgentCore Observability)
   - Risk assessment documentation per NAIC guidance

6. **Policyholder Communication Standards** — Agent-generated communications must meet regulatory requirements
   - Required disclosures in all policyholder communications
   - State-specific language requirements
   - Reading level compliance
   - Translated versions for non-English speakers

### Specific AgentCore Configurations

```yaml
# Insurance Policy Configuration
agentcore_policy:
  automated_reasoning: REQUIRED_FOR_ALL_DECISIONS
  explainability: MANDATORY
  anti_discrimination: ENFORCED
  custom_policies:
    - adverse_action_notice_generation
    - protected_class_factor_prohibition
    - rate_filing_documentation
    - claims_fairness_monitoring
    - policyholder_disclosure_requirements

agentcore_evaluations:
  bias_testing: CONTINUOUS
  disparate_impact_analysis: QUARTERLY
  protected_class_tests: [race, gender, age, disability, national_origin]
  claims_fairness_monitoring: ENABLED
  colorado_ai_act_assessment: ANNUAL

agentcore_observability:
  decision_attribution: REQUIRED
  factor_logging: ALL_INPUTS_AND_WEIGHTS
  retention: 7_YEARS  # Regulatory examination lookback
  examination_report_generation: AUTOMATED
  adverse_action_logging: COMPLETE

agentcore_registry:
  regulatory_filing_metadata: REQUIRED
  model_governance_documentation: LINKED
  annual_review_scheduling: AUTOMATED
  naic_classification: TAGGED
```

### Pattern Modification
- **Centralized** strongly recommended for insurance (regulatory consistency required)
- ALL agents influencing underwriting, pricing, or claims decisions require Tier 3 Policy with Automated Reasoning
- Bias testing is not optional — must be continuous, not one-time
- Regulatory examination documentation must be producible within 24 hours
- Consider separate agent tiers: administrative agents (lower compliance) vs. decision agents (full compliance)
- State-by-state variation means policies must be configurable per jurisdiction

---

## Cross-Industry Common Requirements

Regardless of industry, these requirements apply whenever agents handle sensitive decisions:

### Universal Requirements

| Requirement | AgentCore Component | Configuration |
|---|---|---|
| Audit trail | Observability | Full trace logging, immutable storage |
| Access control | Identity | Least-privilege, delegation chains |
| Data protection | Policy + Memory | Encryption, access logging, purge capability |
| Quality monitoring | Evaluations | Continuous production evaluation |
| Inventory | Registry | Complete agent catalog with ownership |
| Explainability | Policy (Automated Reasoning) | Decision basis documentation |
| Testing | Harness | Pre-deployment validation, regression detection |
| Incident response | Observability + Policy | Detection, alerting, automated remediation |

### Compliance Architecture Decision Tree

```
Is the agent making decisions about people?
├─ YES → Require: Explainability, Bias testing, Audit trails
│   ├─ Financial decisions? → Add: SOX/PCI/OCC overlay
│   ├─ Health decisions? → Add: HIPAA/FDA overlay
│   ├─ Government decisions? → Add: FedRAMP/NIST overlay
│   └─ Insurance decisions? → Add: State reg/NAIC overlay
└─ NO → Standard governance (Tier 1-2 Policy, Tier 1-2 Observability)

Does the agent handle sensitive data?
├─ YES → Require: Encryption, Access logging, DLP, Boundary controls
│   ├─ Payment data? → Add: PCI isolation overlay
│   ├─ Health data? → Add: HIPAA PHI controls
│   ├─ Government data? → Add: Data residency, classification
│   └─ Customer PII? → Add: Privacy overlay (CCPA/GDPR)
└─ NO → Standard data handling (Tier 1 Security)
```

---

## Retrieval Notes for LLM

- When a customer mentions their industry, ALWAYS apply the relevant overlay to the architecture recommendation.
- Overlays are ADDITIVE — they add requirements, never remove capabilities from the base pattern.
- Multiple overlays can apply simultaneously (e.g., healthcare + government for VA/Military health).
- Compliance requirements generally push toward Centralized pattern (easier to audit and enforce).
- If a customer says "we're regulated" without specifics, ask which regulations apply before recommending.
- Automated Reasoning (AgentCore Policy) is the key differentiator for regulated industries — it provides FORMAL PROOF of correctness, not probabilistic assessment.
- Never recommend reduced governance for regulated industries, even if the customer resists. Document the risk if they insist.
- Cost of compliance is real — acknowledge it. But cost of non-compliance is higher (fines, reputation, business loss).
