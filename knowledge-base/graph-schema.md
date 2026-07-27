# Platform Advisor — Knowledge Graph Schema

> **Purpose:** Define the graph structure that powers deterministic-yet-evolvable decision making for the Agentic Platform Advisor.

---

## Design Principles

1. **New knowledge = new nodes/edges, not code changes**
2. **Determinism from traversal rules, not from rigid trees**
3. **Weights are adjustable — calibrated by field experience**
4. **The graph answers: "Given THESE constraints, what MUST the architecture include?"**

---

## Node Types (Entities)

| Node Type | Description | Example | Properties |
|-----------|-------------|---------|------------|
| `Constraint` | Something a customer says/is — an input signal | "10+ LOBs", "Multi-cloud", "Low expertise" | `signal_id`, `question`, `answer_value`, `weight` |
| `Pattern` | A canonical architecture topology | "Centralized", "Federated", "Mesh", "Economy" | `name`, `description`, `maturity_required` |
| `Component` | A fabric building block within a pattern | "Agent Registry", "Policy Engine", "Observability" | `name`, `tier` (1/2/3), `description` |
| `Innovation` | A technology shift that modifies architecture | "Programmatic Tool Calling", "Intelligent Routing" | `name`, `date_emerged`, `status` (current/emerging/deprecated) |
| `Law` | An empirical hard constraint (research-backed) | "Failure Cost Asymmetry → Verifier-Critic" | `name`, `source`, `condition`, `force` |
| `AntiPattern` | A known failure mode | "God Agent", "Single Team Bottleneck" | `name`, `symptoms`, `root_cause`, `fix` |
| `TopologyDecision` | A structural commitment (from Layer 2) | "Agent Topology: Hierarchical" | `decision_id`, `option_selected`, `rationale` |
| `Industry` | A vertical that imposes additional constraints | "Financial Services", "Healthcare", "Government" | `name`, `regulatory_frameworks[]` |
| `AWSService` | A specific AWS service that implements a component | "Bedrock Agents", "Step Functions", "EventBridge" | `name`, `category`, `last_verified` |
| `Phase` | A build phase (P0/P1/P2) | "Foundation (0-3 months)" | `order`, `duration`, `gate_criteria` |

---

## Edge Types (Relationships)

### Constraint → Pattern Edges (Scoring)

These encode the 5-axis affinity scores from the Decision Engine Spec:

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `PRESSURES_TOWARD` | Constraint | Pattern | `weight` (0.0-1.0), `axis` | "10+ LOBs" pressures toward "Federated" with weight 0.9 |
| `PRESSURES_AGAINST` | Constraint | Pattern | `weight` (0.0-1.0), `reason` | "Low expertise" pressures against "Mesh" with weight 0.7 |

**How scoring works:** Traverse all `PRESSURES_TOWARD` edges from active constraints → accumulate weighted scores per pattern → highest score wins.

```
[Constraint: "10+ LOBs"] ──PRESSURES_TOWARD {w:0.9}──→ [Pattern: "Federated"]
[Constraint: "10+ LOBs"] ──PRESSURES_TOWARD {w:0.7}──→ [Pattern: "Mesh"]
[Constraint: "10+ LOBs"] ──PRESSURES_AGAINST {w:0.8}──→ [Pattern: "Centralized"]
[Constraint: "Low expertise"] ──PRESSURES_TOWARD {w:0.8}──→ [Pattern: "Centralized"]
[Constraint: "Low expertise"] ──PRESSURES_AGAINST {w:0.6}──→ [Pattern: "Mesh"]
```

### Pattern → Component Edges (Architecture)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `REQUIRES` | Pattern | Component | `min_tier`, `priority` (P0/P1/P2) | "Federated" requires "Agent Registry" at min Tier 2 |
| `OPTIONAL` | Pattern | Component | `recommended_tier`, `trigger_condition` | "Centralized" optionally includes "Marketplace" if economy_pressure > 0.5 |

```
[Pattern: "Federated"] ──REQUIRES {min_tier:2, priority:P0}──→ [Component: "Agent Registry"]
[Pattern: "Federated"] ──REQUIRES {min_tier:3, priority:P0}──→ [Component: "Identity Mesh"]
[Pattern: "Centralized"] ──REQUIRES {min_tier:1, priority:P0}──→ [Component: "Orchestration Layer"]
```

### Constraint → Component Edges (Tier Elevation)

Some constraints directly force tier requirements regardless of pattern:

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `ELEVATES_TIER` | Constraint | Component | `min_tier`, `reason` | "Full autonomy" elevates "Guardrails" to min Tier 3 |

```
[Constraint: "Full autonomy"] ──ELEVATES_TIER {min:3}──→ [Component: "Guardrails"]
[Constraint: "High cost sensitivity"] ──ELEVATES_TIER {min:2}──→ [Component: "Cost Gateway"]
```

### Industry → Component Edges (Compliance Forces)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `FORCES_TIER` | Industry | Component | `min_tier`, `regulation` | "Healthcare" forces "Policy Engine" to Tier 3 (HIPAA) |
| `REQUIRES_ADDITION` | Industry | Component | `reason` | "Financial Services" requires "Audit Trail" component |

```
[Industry: "Healthcare"] ──FORCES_TIER {min:3, reg:"HIPAA"}──→ [Component: "Policy Engine"]
[Industry: "Financial Services"] ──FORCES_TIER {min:3, reg:"SOX"}──→ [Component: "Audit Trail"]
```

### Innovation → Architecture Edges (Modifications)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `REPLACES` | Innovation | Component | `condition`, `when` | "Programmatic Tool Calling" replaces "MCP Server Layer" when constraint = "MCP is hard" |
| `ENABLES` | Innovation | Pattern | `lowers_barrier`, `since` | "A2A Protocol" enables "Mesh" pattern (lowers coordination cost) |
| `SOLVES` | Innovation | Constraint | `how`, `verified_date` | "Intelligent Routing" solves "Agents too expensive" |

```
[Innovation: "Programmatic Tool Calling"] ──REPLACES {when:"MCP is hard"}──→ [Component: "MCP Server Layer"]
[Innovation: "Intelligent Routing"] ──SOLVES──→ [Constraint: "Agents too expensive"]
[Innovation: "A2A Protocol"] ──ENABLES {since:"2025-Q4"}──→ [Pattern: "Mesh"]
```

### Law → Architecture Edges (Hard Constraints)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `FORCES` | Law | TopologyDecision | `condition`, `override_score` | "Failure Cost Asymmetry" forces "Verifier-Critic" sub-pattern |
| `BLOCKS` | Law | Pattern | `condition`, `reason` | "Coordination Overhead > 30%" blocks "Mesh" for low-volume workloads |

```
[Law: "Failure Cost Asymmetry"] ──FORCES {if:"risk_asymmetry=high"}──→ [TopologyDecision: "Verifier-Critic gate"]
[Law: "Coordination Overhead"] ──BLOCKS {if:"volume=low"}──→ [Pattern: "Mesh"]
```

### AntiPattern → Architecture Edges (Warnings)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `TRIGGERED_BY` | AntiPattern | Pattern + Constraint combo | `conditions[]` | "God Agent" triggered by Centralized + High LOB count + No Registry |
| `PREVENTED_BY` | AntiPattern | Component | `min_tier` | "God Agent" prevented by "Agent Registry" at Tier 2+ |

```
[AntiPattern: "God Agent"] ──TRIGGERED_BY {if:["centralized", "lob>5", "no_registry"]}──→ [Pattern: "Centralized"]
[AntiPattern: "God Agent"] ──PREVENTED_BY {min_tier:2}──→ [Component: "Agent Registry"]
```

### Component → AWS Service Edges (Implementation)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `IMPLEMENTED_BY` | Component | AWSService | `tier`, `config_notes` | "Orchestration Layer" at Tier 2 implemented by "Step Functions" |
| `ALTERNATIVE` | AWSService | AWSService | `when`, `trade_off` | "Strands SDK" alternative to "Bedrock Agents" when multi-cloud |

```
[Component: "Orchestration Layer", Tier:1] ──IMPLEMENTED_BY──→ [AWSService: "Bedrock Agents"]
[Component: "Orchestration Layer", Tier:2] ──IMPLEMENTED_BY──→ [AWSService: "Step Functions + Bedrock"]
[Component: "Orchestration Layer", Tier:3] ──IMPLEMENTED_BY──→ [AWSService: "Strands SDK custom"]
```

### Component → Phase Edges (Sequencing)

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `BUILT_IN` | Component | Phase | `pattern`, `dependency` | "Agent Registry" built in P0 for Federated pattern |
| `DEPENDS_ON` | Component | Component | `reason` | "Policy Engine" depends on "Agent Registry" (can't govern what you don't track) |

```
[Component: "Agent Registry"] ──BUILT_IN {pattern:"federated"}──→ [Phase: "P0"]
[Component: "Policy Engine"] ──DEPENDS_ON──→ [Component: "Agent Registry"]
```

---

## Graph Traversal Algorithm (The "Decision" Process)

### Step 1: Activate Constraints

User answers 12 questions → creates 12 active `Constraint` nodes.

### Step 2: Compute Pattern Scores

```
FOR each active Constraint:
    TRAVERSE all PRESSURES_TOWARD edges → accumulate weight × constraint.weight per Pattern
    TRAVERSE all PRESSURES_AGAINST edges → subtract weight × constraint.weight per Pattern
    
RESULT: ranked Pattern scores
```

### Step 3: Apply Laws (Hard Override)

```
FOR each Law:
    IF Law.condition matches active constraints:
        IF Law has BLOCKS edge → remove blocked Pattern from candidates
        IF Law has FORCES edge → inject forced TopologyDecision
        
RESULT: filtered Pattern candidates + forced decisions
```

### Step 4: Select Pattern + Determine Components

```
SELECT highest-scoring non-blocked Pattern

FOR selected Pattern:
    TRAVERSE all REQUIRES edges → collect Components with min_tier
    TRAVERSE all OPTIONAL edges → include if trigger_condition met
    
RESULT: Component list with base tiers
```

### Step 5: Elevate Tiers (Constraints + Industry)

```
FOR each active Constraint:
    TRAVERSE ELEVATES_TIER edges → raise Component tiers where applicable

IF Industry specified:
    TRAVERSE FORCES_TIER edges → raise Component tiers to compliance minimums
    TRAVERSE REQUIRES_ADDITION edges → add mandatory components
    
RESULT: Component list with final tiers
```

### Step 6: Apply Innovations

```
FOR each active Constraint:
    TRAVERSE to matching Innovations (via SOLVES edges)
    FOR each Innovation:
        IF Innovation has REPLACES edge → swap Component
        IF Innovation has ENABLES edge → unlock Pattern options
        
RESULT: Modified architecture with innovation overlays
```

### Step 7: Check Anti-Patterns

```
FOR selected Pattern + active Constraints:
    TRAVERSE TRIGGERED_BY edges on all AntiPatterns
    IF conditions match:
        CHECK if PREVENTED_BY component exists at required tier
        IF NOT → flag WARNING
        
RESULT: Risk warnings
```

### Step 8: Determine Phasing

```
FOR each required Component:
    TRAVERSE BUILT_IN edges → assign to Phase
    TRAVERSE DEPENDS_ON edges → validate dependency ordering
    
RESULT: Sequenced build roadmap (P0 → P1 → P2)
```

### Step 9: Map to AWS Services

```
FOR each Component at determined tier:
    TRAVERSE IMPLEMENTED_BY edges → select AWS service
    CHECK for ALTERNATIVE edges if multi-cloud constraint active
    
RESULT: Service map
    → THEN: Call MCP for live details (pricing, workshops, latest features)
```

---

## What Changes When You Learn Something New

| You Learn... | Graph Operation | Code Change? |
|-------------|-----------------|--------------|
| New customer constraint matters | Add `Constraint` node + `PRESSURES_TOWARD` edges | ❌ None |
| A pattern doesn't work for situation X | Add `PRESSURES_AGAINST` edge or adjust weight | ❌ None |
| New innovation launched | Add `Innovation` node + `SOLVES`/`REPLACES`/`ENABLES` edges | ❌ None |
| New empirical law discovered | Add `Law` node + `FORCES`/`BLOCKS` edges | ❌ None |
| Industry requires new compliance | Add `FORCES_TIER` edge from Industry → Component | ❌ None |
| Existing recommendation failed | Reduce edge weight or add `AntiPattern` node | ❌ None |
| New architecture pattern emerges | Add `Pattern` node + `REQUIRES` edges + constraint edges | ❌ None |
| New AWS service replaces old one | Update `IMPLEMENTED_BY` edges | ❌ None |
| Scoring weights are wrong | Adjust `weight` property on edges | ❌ None |
| New component needed for a pattern | Add `Component` node + `REQUIRES` edge | ❌ None |

**Every single evolution is a graph mutation, never a code change.**

---

## Graph Size Estimate (MVP)

| Node Type | Count | Source |
|-----------|-------|--------|
| Constraints | ~36 (12 questions × 3 answer values) | Decision Engine Spec v2 |
| Patterns | 4-5 | Your canonical patterns |
| Components | 9-12 | Fabric Maturity model |
| Innovations | 15-20 | Constraint-Innovation Map |
| Laws | 5-7 | Research papers, field experience |
| AntiPatterns | 10-15 | Your anti-pattern catalog |
| Industries | 5-8 | Common verticals |
| AWSServices | 20-30 | Service mapping |
| Phases | 3 | P0, P1, P2 |
| TopologyDecisions | 6 | Layer 2 decisions |

**Total: ~120-150 nodes, ~400-600 edges**

This is small enough to:
- Store as JSON in a Quick Space (MVP)
- Load entirely into memory for traversal
- Visualize for debugging
- Eventually migrate to Neptune/DynamoDB

---

## Implementation Path

| Phase | Graph Storage | Traversal Engine | Maintenance |
|-------|--------------|------------------|-------------|
| **Now** | JSON file in Quick Space | LLM follows traversal instructions in system prompt | Manual (you edit JSON) |
| **Month 1** | JSON in S3 + Quick Automate | Code Action (Python) does traversal deterministically | Semi-auto (LLM proposes, you approve) |
| **Month 2** | Neptune Serverless or DynamoDB | Gremlin/Cypher queries or custom API | Agentic updater (monitors sources, proposes edges) |
| **Month 3** | Same + versioning | Same + A/B testing different weights | Feedback loop from engagement outcomes |

---

## Example: Full Traversal for a Customer Scenario

**Input:** "We have 10+ LOBs, multi-cloud, low expertise, cost is #1 concern, MCP is hard to deploy"

```
Step 2: Score
  - "10+ LOBs" → Federated: +0.9, Mesh: +0.7, Centralized: -0.8
  - "Multi-cloud" → Mesh: +0.6, Federated: +0.4, Centralized: -0.5
  - "Low expertise" → Centralized: +0.8, Federated: -0.3, Mesh: -0.6
  - "Cost sensitive" → Centralized: +0.5, Economy: +0.3
  
  SCORES: Federated: 2.1, Centralized: 1.2, Mesh: 0.9, Economy: 0.4
  → Selected: FEDERATED

Step 3: Laws
  - Law "Coordination Overhead" check → volume not low → Mesh not blocked
  - No forced decisions triggered

Step 4: Components
  - Federated REQUIRES: Agent Registry (T2), Identity Mesh (T2), 
    Policy Engine (T2), Orchestration (T1), Observability (T2)

Step 5: Elevate
  - "Cost sensitive" ELEVATES "Cost Gateway" to T2
  - "Low expertise" ELEVATES "Self-Service Portal" to T2
  - No industry specified → skip

Step 6: Innovations
  - "MCP is hard" → Innovation: "Programmatic Tool Calling" REPLACES "MCP Server Layer"
  - "Cost sensitive" → Innovation: "Intelligent Routing" SOLVES → add "Inference Gateway" component

Step 7: Anti-Patterns
  - Federated + Low expertise → WARNING: "Capability Gap" (teams can't self-serve)
  - PREVENTED_BY: "Self-Service Portal" at T2 ✓ (already elevated)

Step 8: Phasing
  - P0: Agent Registry, Policy Engine, Observability (foundations)
  - P1: Identity Mesh, Cost Gateway, Self-Service Portal
  - P2: Inference Gateway, Advanced orchestration

Step 9: AWS Services (via MCP)
  - Agent Registry T2 → DynamoDB + custom API
  - Identity Mesh T2 → IAM + STS + custom token service
  - Policy Engine T2 → Bedrock Guardrails + Step Functions
  - ...
```

**Output:** A fully deterministic, explainable, traceable blueprint.

---

## Open Design Questions

1. **Conflict resolution:** When two Laws conflict (one forces, one blocks), which wins? → Propose: Laws have priority scores.
2. **Hybrid patterns:** When scores are close (Federated: 2.1 vs Mesh: 1.9), recommend hybrid? → Propose: If gap < 20%, recommend "Federated with Mesh characteristics."
3. **Weight calibration:** How do you adjust weights over time? → Propose: After each engagement, record whether recommendation was accepted/modified → adjust weights ±0.05.
4. **Versioning:** When the graph changes, should old traversals be reproducible? → Propose: Version the graph, tag each output with graph version.
