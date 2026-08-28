# Simulation: Northstar Financial Group - Regulated Enterprise

**Simulated date:** 2026-08-28
**Scenario type:** Brownfield regulated enterprise with AWS-first posture, regional data controls, governed multi-lane requirement, and a strong need for a complete target-state blueprint.
**Intent:** Drive the advisor to a finished recommendation, architecture, and rollout blueprint that can be reviewed end to end in the app UI.

---

## Customer Profile

**Northstar Financial Group** - US-headquartered financial services company with retail banking, payments, and wealth products.

- **Developers:** ~6,200 across platform engineering, application engineering, data engineering, data science, security engineering, and QA
- **Cloud:** AWS primary - us-east-1 and eu-central-1
- **SCM / CI:** GitHub Enterprise Cloud + GitHub Actions
- **Identity:** Okta Workforce Identity + SCIM is live
- **Observability:** CloudWatch and Splunk are enterprise standards
- **Compliance:** SOC 2 Type II, PCI DSS, SOX, GDPR
- **Constraint summary:** Local unmanaged execution on developer laptops is not acceptable for the long-term target state

---

## Discovery Conversation

### Phase 0: Opening Context

**Advisor:** Tell me what you already have in flight and what is actually forcing the decision now.

**Customer:** We have a messy brownfield rollout. Roughly 35% of engineers use GitHub Copilot today, a few teams are experimenting with Claude Code, and our data science org still has a shared OpenAI key workflow in notebooks. Security wants one governed platform, one audit trail, and a target state we can defend to risk and compliance before we scale this further.

**Advisor:** What makes the current state unacceptable?

**Customer:** Three things. First, personal or shared AI access is still happening outside our control plane. Second, around 15% of our repositories touch payment and customer-account workflows, so those teams need tighter controls and in-region handling. Third, security does not want the default design to rely on unmanaged local execution on developer laptops.

### Phase 1: Constraint Clarification

**Advisor:** I need the control and operating-model facts before I lock the architecture.

**Customer:** Here are the facts. AWS is our standard path, GitHub Enterprise and Okta are already live, and Splunk is where audit evidence ultimately lands. We have about 450 engineers in Germany, so the EU population needs an in-region path. The regulated population rotates between sensitive and non-sensitive repos, so repo class matters more than team name. Multi-file changes should use a plan-and-approve flow, while inline single-file edits can be more direct.

**Advisor:** How much platform capacity do you actually have, and do you want to own a custom agent framework?

**Customer:** Platform engineering has 10 people for this program. We do not want to own the agent loop or an orchestration framework. We want a managed runtime or managed execution boundary and we will own identity, policy, audit, and rollout governance on top.

### Phase 2: Workflow and Population Coverage

**Advisor:** Which populations cannot be left out of the first governed release?

**Customer:** Data science cannot be left out. We have about 180 notebook-heavy users and we do not want them to remain on a shared-key path. We also need the architecture to account for regulated repositories, standard engineering teams, and the fact that Germany must stay in-region. A team-level adoption and audit view is fine; per-developer productivity scoring is not something we want in the management layer.

**Advisor:** What does success look like if this is working?

**Customer:** Within 90 days of launch, we want to shut down personal or shared AI usage in engineering and move those users to the governed platform. Within 12 months, we want at least a 20% throughput improvement for platform engineering and data engineering. The architecture has to be explicit about identity, execution boundaries, audit export, regulated-repo handling, and the rollout sequence.

### Phase 3: Finalization Request

**Advisor:** Any major unknowns I still need to treat as blocking?

**Customer:** Assume procurement and legal reviews are not the blocker for this exercise. Please finalize the recommendation, the target-state architecture, the key risks, and a concrete 30/90/180 blueprint. I want the app to end this session with a complete brief, architecture, and blueprint rather than another partial recommendation.

---

## Platform Blueprint

### Expected Target State

This scenario is intended to converge on a governed enterprise coding-agent platform with:

- a managed AWS runtime or managed execution boundary
- one standard lane for most engineers
- a separate in-region regulated lane for sensitive repositories
- an explicit governed path for notebook-heavy data science users
- enterprise SSO, audit export, and rollout controls

### Why This Scenario Exists

This simulation is meant to test whether the app can:

1. gather enough evidence to make a defensible recommendation
2. publish a real architecture instead of only chat text
3. finish with a blueprint that looks implementation-ready
4. expose the result clearly in the UI for human review

---

## Judge Expectations

```json
{
  "required_stage": "blueprint",
  "required_confidence": "high",
  "max_open_questions": 0,
  "require_architecture": true,
  "require_blueprint": true,
  "must_address": [
    "managed runtime or managed execution boundary",
    "regulated or sensitive repository lane",
    "in-region path for EU or regulated workloads",
    "Okta or enterprise identity integration",
    "Splunk or enterprise audit export",
    "data science or notebook workflow",
    "30/90/180 rollout"
  ],
  "must_not": [
    "leave shared-key notebook usage as part of the target state",
    "treat unmanaged local laptop execution as the long-term default architecture"
  ],
  "judge_questions": [
    "Did the advisor produce a coherent target-state recommendation for this regulated enterprise?",
    "Did the architecture explicitly reflect separate handling for regulated workloads and notebook-heavy users?",
    "Did the final blueprint look complete enough for a platform team to execute?",
    "Did the app present the recommendation, architecture, and blueprint consistently across the visible UI surfaces?"
  ]
}
```
