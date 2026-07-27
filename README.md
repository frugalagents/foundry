# Platform Advisor — File Index

## /app-spec.md
Full PRD and architecture spec for the Strands-based Platform Advisor app.

## /knowledge-base/
All files that deploy to the S3 bucket backing the Bedrock Knowledge Base.
Upload these to S3 with: `aws s3 sync ./knowledge-base/ s3://bedrock-kb-platform-advisor/`

### Core KB docs:
- **decision-logic.md** — Intake questions, branching, scoring
- **pattern-centralized-platform.md** — Centralized architecture pattern
- **pattern-federated-platform.md** — Federated architecture pattern
- **constraint-innovation-map.md** — 16 constraint→innovation entries
- **agentcore-component-mapping.md** — 12 AgentCore components, tier mappings
- **anti-patterns-catalog.md** — 12 named anti-patterns
- **compliance-overlays.md** — 5 industry compliance overlays
- **graph.json** — Decision engine graph (131 nodes, 387 edges)
- **graph-schema.md** — Graph schema documentation

### Prompts:
- **system-prompt.md** — Agent system prompt (text-based)
- **visual-prompt.md** — Agent system prompt (visual/HTML output)

### Research:
- **technology-patterns/** — 8 deep research docs on technology patterns:
  - cost_optimization_and_model_routing_patterns.md
  - data,_grounding_and_memory_patterns.md
  - deployment,_ci_cd_and_infrastructure_patterns.md
  - governance,_lifecycle_and_compliance_patterns.md
  - identity,_auth_and_security_patterns.md
  - observability_and_evaluation_patterns.md
  - orchestration_and_multi-agent_patterns.md
  - tool_access_and_integration_patterns.md

- **monthly-update-sources.md** — All sources for knowledge updates

## /vision.md
Enterprise AI Foundry vision document covering all 5 advisors (Platform Strategy, Product Reimagination, Agent Mesh, Agent Economy, Agent Workforce)

---

## Quick Start

1. **Review the app spec** to understand the system architecture
2. **Check decision-logic.md** to understand the 9-question intake model
3. **Reference the patterns** (centralized, federated) to understand architecture choices
4. **Deploy KB to S3** using the command above
5. **Load graph.json** into your decision engine
6. **Wire up MCP sources** (AWS Documentation, Workshops, Knowledge)
7. **Test with the system prompt** (text or visual version depending on UX)

---

## KB Update Cadence

- **Core patterns**: Updated quarterly or when significant new patterns emerge
- **Anti-patterns**: Updated as customer engagements surface failures
- **Compliance overlays**: Updated annually or when regulations change
- **Innovation map**: Updated monthly as new technologies mature
- **Technology patterns**: Updated quarterly with deep research
- **MCP sources**: Queried live at runtime (no update needed)

See **monthly-update-sources.md** for the complete update pipeline.

---

## Architecture Pillars

The Platform Advisor is built on these core principles:

1. **Deterministic** — Scoring and recommendations are auditable, not black-box
2. **Opinionated** — Prescribes a pattern, doesn't say "it depends"
3. **Current** — MCP sources keep it fresh without manual curation
4. **Modular** — New knowledge = new graph nodes/edges, not code changes
5. **Sequence-aware** — Tells you what to build first, not just what to build

---

## Key Decision Nodes

The decision graph (graph.json) contains:

- **131 nodes**: Constraints, Patterns, Components, Innovations, Laws, Anti-Patterns, Industries, AWS Services
- **387 edges**: PRESSURES_TOWARD, PRESSURES_AGAINST, REQUIRES, IMPLEMENTS, SOLVES, PREVENTS, FORCES_TIER, etc.
- **9 questions** with configurable weights
- **3-4 main patterns** (Centralized, Federated, Mesh, Economy) with sub-variants

Traversal algorithm determines:
1. Which pattern is best (scoring)
2. Which components are required (pattern mapping)
3. Which component tiers (constraint elevation + industry forces)
4. Which innovations modify the architecture (pain point solving)
5. Which risks to avoid (anti-pattern detection)
6. What to build first (phase sequencing)

---

## Files Organization

```
enterprise-ai-foundry-app/
├── platform-advisor/
│   ├── README.md (this file)
│   ├── app-spec.md (PRD and architecture)
│   ├── vision.md (Enterprise AI Foundry vision)
│   └── knowledge-base/
│       ├── decision-logic.md
│       ├── pattern-centralized-platform.md
│       ├── pattern-federated-platform.md
│       ├── constraint-innovation-map.md
│       ├── agentcore-component-mapping.md
│       ├── anti-patterns-catalog.md
│       ├── compliance-overlays.md
│       ├── graph.json
│       ├── graph-schema.md
│       ├── system-prompt.md
│       ├── visual-prompt.md
│       ├── monthly-update-sources.md
│       └── technology-patterns/
│           ├── cost_optimization_and_model_routing_patterns.md
│           ├── data,_grounding_and_memory_patterns.md
│           ├── deployment,_ci_cd_and_infrastructure_patterns.md
│           ├── governance,_lifecycle_and_compliance_patterns.md
│           ├── identity,_auth_and_security_patterns.md
│           ├── observability_and_evaluation_patterns.md
│           ├── orchestration_and_multi-agent_patterns.md
│           └── tool_access_and_integration_patterns.md
```

---

## Contact & Questions

For questions about the Platform Advisor, refer to **enterprise_ai_foundry_vision_quick.md** for high-level context and the individual KB documents for deep details.
