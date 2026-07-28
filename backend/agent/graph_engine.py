"""
Deterministic graph traversal engine for the Platform Advisor.

Graph schema (from graph.json):
  nodes:  { "id": "...", "type": "Pattern|Constraint|Component|...", "props": {...} }
  edges:  { "from": "...", "to": "...", "type": "PRESSURES_TOWARD|...", "props": {...} }

Constraint nodes carry pressure fields in props:
  centralization_pressure, federation_pressure, mesh_pressure,
  economy_pressure, simplicity_pressure  (0.0–1.0)

Edge types used for scoring:
  PRESSURES_TOWARD / PRESSURES_AGAINST

Edge types for component mapping:
  REQUIRES, IMPLEMENTS, IMPLEMENTED_BY, BUILT_IN, DEPENDS_ON

Edge types for tier elevation:
  ELEVATES_TIER, FORCES_TIER, FORCES

Anti-pattern edges:
  TRIGGERED_BY (constraint → anti-pattern)
  PREVENTED_BY (component → anti-pattern)
"""
from __future__ import annotations
from typing import Optional


PATTERN_AXIS: dict[str, int] = {
    "pattern:centralized": 0,
    "pattern:federated":   1,
    "pattern:mesh":        2,
    "pattern:economy":     3,
}

SIMPLICITY_AXIS = 4

AXIS_LABELS = ["Centralization", "Federation", "Mesh", "Economy", "Simplicity"]

PRESSURE_KEYS = [
    "centralization_pressure",
    "federation_pressure",
    "mesh_pressure",
    "economy_pressure",
    "simplicity_pressure",
]


class GraphEngine:
    """In-memory graph traversal for deterministic scoring and component selection."""

    # Map app-facing intake keys → graph Constraint signal_id.
    # Answer→constraint matching is scoped to the answer's own signal group so a
    # value never collides with a same-substring answer_value under a different
    # question (e.g. data-location "single" matching "1-3 teams (single org)").
    # Keys with no graph signal yet (governance_model, stack_preference,
    # auth_identity, observability, intake_maturity) are intentionally absent and
    # contribute no pressure until the graph adds matching constraints.
    _INTAKE_TO_SIGNAL: dict[str, str] = {
        "autonomy_model":    "Q1",
        "team_expertise":    "Q2",
        "lob_count":         "Q3",
        "agent_purpose":     "Q4",
        "cloud_posture":     "Q5",
        "data_gravity":      "Q6",
        "cost_sensitivity":  "Q7",
        "compliance_regime": "Q8",
    }

    # Map short intake form values → keywords that appear in the graph constraint
    # answer_value text (which is long-form). Shared by scoring + signal display.
    _ANSWER_EXPANSIONS: dict[str, list[str]] = {
        # autonomy_model (Q1)
        "full":          ["full autonomy", "independently"],
        "hitl":          ["humans approve", "approval gates", "human-in-the-loop"],
        "supervised":    ["copilot", "humans execute", "supervised"],
        # team_expertise (Q2)
        "high":          ["dedicated", "ai/ml engineers", "engineers"],
        "medium":        ["full-stack", "developer"],
        "low":           ["no-code", "business"],
        # lob_count (Q3) — values "1-3","4-10","10+" substring-match directly
        # agent_purpose (Q4)
        "internal":      ["internal", "back-office"],
        "customer_facing": ["customer-facing", "customer facing"],
        "both":          ["mix of all", "both"],
        # cloud_posture (Q5)
        "single_aws":    ["all-in on aws", "all-in on amazon"],
        "aws_primary":   ["aws-primary", "aws primary"],
        "multi_cloud":   ["2+ clouds", "multi-cloud", "multiple clouds"],
        "on_prem":       ["on-prem", "edge"],
        # data_gravity (Q6)
        "single_region": ["single aws region", "single region"],
        "multi_region":  ["multiple aws regions", "multi-region", "multiple region"],
        "on_prem_cloud": ["hybrid", "on-prem"],
        "edge":          ["edge", "distributed"],
        # cost_sensitivity (Q7)
        "primary":       ["#1 constraint", "cost is the", "optimize from day"],
        "secondary":     ["performance first"],
        "optimize_later": ["predictable spend", "fixed budget"],
        # compliance_regime (Q8) — values match the spec's Q6 list / graph nodes
        "hipaa":         ["hipaa", "health"],
        "sox":           ["sox", "financial controls"],
        "eu_ai_act":     ["eu ai act"],
        "gdpr":          ["gdpr"],
        "pci_dss":       ["pci", "payment"],
        "fedramp":       ["fedramp", "fisma", "government"],
        "none":          ["none", "internal only"],
    }

    def _match_constraint(self, intake_key: str, single_val: str) -> Optional[dict]:
        """Find the Constraint node for an intake (key, value), scoped to the key's
        signal group. Returns None if the key has no signal or nothing matches."""
        signal = self._INTAKE_TO_SIGNAL.get(intake_key)
        if not signal:
            return None
        search_terms = [single_val.lower()] + [
            kw.lower() for kw in self._ANSWER_EXPANSIONS.get(single_val, [])
        ]
        for node in self.get_nodes_by_type("Constraint"):
            props = self.get_props(node["id"])
            if props.get("signal_id") != signal:
                continue
            av = props.get("answer_value", "").lower()
            if any(term in av for term in search_terms):
                return node
        return None

    def __init__(self, graph_data: dict) -> None:
        # Index nodes by id
        self.nodes: dict[str, dict] = {}
        for node in graph_data.get("nodes", []):
            nid = node.get("id") or node.get("node_id")
            if nid:
                self.nodes[nid] = node

        self.edges: list[dict] = graph_data.get("edges", [])

        # Build edge indexes: by source and by type
        self._out_edges: dict[str, list[dict]] = {}
        self._in_edges: dict[str, list[dict]] = {}
        for edge in self.edges:
            src = edge.get("from") or edge.get("source")
            tgt = edge.get("to") or edge.get("target")
            if src:
                self._out_edges.setdefault(src, []).append(edge)
            if tgt:
                self._in_edges.setdefault(tgt, []).append(edge)

    # ── Node lookups ─────────────────────────────────────────

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        return [n for n in self.nodes.values() if n.get("type") == node_type]

    def get_props(self, node_id: str) -> dict:
        node = self.nodes.get(node_id, {})
        return node.get("props", node)  # fallback: node itself if flat

    def get_out_edges(self, node_id: str, edge_type: Optional[str] = None) -> list[dict]:
        edges = self._out_edges.get(node_id, [])
        if edge_type:
            return [e for e in edges if e.get("type") == edge_type]
        return edges

    def get_in_edges(self, node_id: str, edge_type: Optional[str] = None) -> list[dict]:
        edges = self._in_edges.get(node_id, [])
        if edge_type:
            return [e for e in edges if e.get("type") == edge_type]
        return edges

    # ── Pattern scoring ──────────────────────────────────────

    def compute_pattern_scores(self, answers: dict) -> dict[str, dict]:
        """
        Compute 5-axis affinity scores for each pattern.

        The constraint nodes carry pressure values directly in their props
        (centralization_pressure, federation_pressure, …).  We use these
        together with the edge weight from PRESSURES_TOWARD/AGAINST edges
        for a weighted sum.

        Returns: { "pattern:centralized": {"total": float, "axes": [f]*5}, … }
        """
        pattern_nodes = self.get_nodes_by_type("Pattern")
        pattern_ids = [n["id"] for n in pattern_nodes]
        scores: dict[str, float] = {p: 0.0 for p in pattern_ids}
        axis_scores: dict[str, list[float]] = {p: [0.0] * 5 for p in pattern_ids}

        for _q_key, answer_val in answers.items():
            if _q_key in ("industry", "pain_points"):
                continue

            # Normalise to a list so multi-select answers are each processed
            values: list[str] = answer_val if isinstance(answer_val, list) else [answer_val]

            for single_val in values:
                if not isinstance(single_val, str):
                    continue

                # Match the answer to a constraint within its OWN signal group,
                # so it never collides with a same-substring answer under another
                # question.
                matched = self._match_constraint(_q_key, single_val)
                if matched is None:
                    continue

                props = self.get_props(matched["id"])
                q_weight = float(props.get("weight", 0.1))

                # Use pressure values directly from props
                pressures = [float(props.get(pk, 0.0)) for pk in PRESSURE_KEYS]

                for pid in pattern_ids:
                    axis_idx = PATTERN_AXIS.get(pid)
                    if axis_idx is None:
                        continue

                    # Direct pressure
                    direct = pressures[axis_idx] * q_weight
                    scores[pid] += direct
                    axis_scores[pid][axis_idx] += direct
                    axis_scores[pid][SIMPLICITY_AXIS] += pressures[SIMPLICITY_AXIS] * q_weight

                # Also process explicit PRESSURES_TOWARD / PRESSURES_AGAINST edges
                for edge in self.get_out_edges(matched["id"], "PRESSURES_TOWARD"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt in scores:
                        w = float((edge.get("props") or {}).get("weight", 0.5))
                        scores[tgt] += w * q_weight

                for edge in self.get_out_edges(matched["id"], "PRESSURES_AGAINST"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt in scores:
                        w = float((edge.get("props") or {}).get("weight", 0.5))
                        scores[tgt] -= w * q_weight

        return {
            pid: {"total": scores[pid], "axes": axis_scores[pid]}
            for pid in pattern_ids
        }

    def apply_laws(self, scores: dict[str, dict], answers: dict) -> dict[str, dict]:
        """Disqualify patterns blocked by Law nodes whose trigger matches the answers.

        A law only fires when it carries a non-empty `trigger_condition` dict AND
        every key/value in it matches the intake answers. A law with no (or empty)
        trigger_condition never fires — otherwise `all()` over an empty condition is
        vacuously True and the law would disqualify its BLOCKS targets on every input.
        """
        for node in self.get_nodes_by_type("Law"):
            props = self.get_props(node["id"])
            trigger = props.get("trigger_condition") or {}
            triggered = (
                isinstance(trigger, dict)
                and len(trigger) > 0
                and all(
                    self._answer_matches_trigger(answers.get(k), v)
                    for k, v in trigger.items()
                )
            )
            if not triggered:
                continue
            for edge in self.get_out_edges(node["id"], "BLOCKS"):
                tgt = edge.get("to") or edge.get("target")
                if tgt in scores:
                    scores[tgt]["total"] = -999.0
        return scores

    @staticmethod
    def _answer_matches_trigger(answer, expected) -> bool:
        """True if the intake `answer` satisfies a law trigger `expected` value.

        Supports scalar answers and multi-select (list) answers. `expected` may be a
        single value or a list of acceptable values (any-of).
        """
        expected_vals = expected if isinstance(expected, list) else [expected]
        expected_norm = {str(e).lower() for e in expected_vals}
        if isinstance(answer, list):
            answer_norm = {str(a).lower() for a in answer}
            return bool(answer_norm & expected_norm)
        return str(answer or "").lower() in expected_norm

    # Human-readable explanations for key signal+answer+direction combinations.
    # Key: (question_key, answer_value_lowercase, is_positive_for_winning_pattern)
    _SIGNAL_REASONS: dict[tuple, str] = {
        # lob_count
        ("lob_count", "10+", True):  "10+ LOBs cannot share a single platform — each needs autonomy to innovate independently while a shared spine provides governance",
        ("lob_count", "4-10", True): "Multiple LOBs benefit from federated nodes that allow independent deployment without central bottlenecks",
        ("lob_count", "1-3", False): "A small team count means a single centralized platform is simpler and cheaper to operate",
        # governance_model
        ("governance_model", "undecided", True):  "Undecided governance is built incrementally — federated architecture lets each LOB adopt governance at its own pace",
        ("governance_model", "federated", True):  "Your stated governance model directly matches the federated platform topology",
        ("governance_model", "centralized", False): "Centralized governance requires a single control plane — federated nodes add complexity without benefit",
        # autonomy_model
        ("autonomy_model", "supervised", False): "Supervised (copilot) agents require centralized oversight and approval workflows, not LOB-level autonomy",
        ("autonomy_model", "full", True):  "Fully autonomous agents need per-LOB guardrails and blast-radius containment — federated topology provides this",
        ("autonomy_model", "hitl", False): "Human-in-the-loop gates are best managed from a centralized approval workflow platform",
        # data_gravity
        ("data_gravity", "multi_region", True): "Multi-region data requires regional federation nodes — agents execute close to data, reducing latency and meeting residency rules",
        ("data_gravity", "single_region", False): "Single-region data removes the need for distributed nodes — centralized architecture is simpler and sufficient",
        ("data_gravity", "on_prem_cloud", False): "Hybrid on-prem/cloud data gravity favors a mesh architecture with distributed execution over federation",
        ("data_gravity", "edge", False): "Edge-distributed data favors decentralized mesh topology over federated",
        # cloud_posture
        ("cloud_posture", "multi_cloud", True):  "Multi-cloud workloads need federated nodes per cloud provider with portable orchestration and MCP bridges",
        ("cloud_posture", "single_aws", False):  "All-in AWS enables maximum use of managed AgentCore services — centralized architecture is simplest",
        ("cloud_posture", "aws_primary", False): "AWS-primary workloads centralize the control plane; non-AWS tools connect via AgentCore Gateway bridges",
        ("cloud_posture", "on_prem", False):     "On-prem/edge requirements favor mesh topology for distributed execution close to data",
        # intake_maturity
        ("intake_maturity", "emerging", False): "Emerging AI maturity means shared centralized foundations are essential — federated complexity requires maturity to manage safely",
        ("intake_maturity", "mature", True):    "Mature AI organizations have the operational discipline to run federated nodes without losing governance",
        # agent_purpose
        ("agent_purpose", "customer_facing", True):  "Customer-facing agents need per-LOB customization and SLA ownership — federated pattern enables this without central bottlenecks",
        ("agent_purpose", "internal", False):        "Internal-only agents favor centralized deployment for cost efficiency and simpler governance",
        ("agent_purpose", "both", True):             "Mixed internal and customer-facing purposes across LOBs favors federated to give each LOB the right deployment model",
        # team_expertise
        ("team_expertise", "high", True):  "High expertise teams can safely manage federated complexity and operate independent agent stacks",
        ("team_expertise", "low", False):  "Lower expertise benefits from centralized abstractions — platform team owns the stack, LOBs consume via APIs",
        ("team_expertise", "medium", False): "Medium expertise teams are better served by centralized managed services with extension points",
        # cost_sensitivity
        ("cost_sensitivity", "primary", False):      "Cost-first priority favors centralized token budgets, shared caching, and unified cost governance",
        ("cost_sensitivity", "secondary", True):     "Performance-first priority allows federated deployments optimized independently per LOB",
        ("cost_sensitivity", "optimize_later", False): "Predictable-spend model favors centralized budget caps and per-LOB quota management",
        # stack_preference
        ("stack_preference", "open_source", True):   "Open-source stack preference aligns with federated — teams can choose frameworks per LOB without platform-level lock-in",
        ("stack_preference", "managed", False):       "Managed services preference favors centralized AgentCore ecosystem with maximum AWS integrations",
        ("stack_preference", "hybrid", True):         "Hybrid stack preference fits federated — each LOB can use its preferred toolchain against shared platform services",
        # auth_identity
        ("auth_identity", "complex_multi", True):    "Complex multi-IdP identity maps to per-LOB federated identity federation with a shared central identity plane",
        ("auth_identity", "iam_heavy", False):        "IAM-heavy identity is best centralized — all agents authenticate through a single IAM-governed control plane",
        ("auth_identity", "oauth_oidc", True):        "OAuth/OIDC identity supports federated agent identity where each LOB manages its own scopes",
    }

    def compute_scoring_signals(self, answers: dict, pattern_id: str) -> list[dict]:
        """
        Return the top intake signals that drove the score for `pattern_id`.

        Each entry: {signal, value, contribution (float), direction ("positive"|"negative")}
        Sorted by absolute contribution descending.
        """
        axis_idx = PATTERN_AXIS.get(pattern_id)
        if axis_idx is None:
            return []

        _QUESTION_LABELS: dict[str, str] = {
            "autonomy_model":   "Autonomy Model",
            "team_expertise":   "Team Expertise",
            "cloud_posture":    "Cloud Stance",
            "stack_preference": "Stack Preference",
            "lob_count":        "Lines of Business",
            "governance_model": "Governance Model",
            "auth_identity":    "Auth & Identity",
            "observability":    "Observability",
            "intake_maturity":  "AI Maturity",
            "agent_purpose":    "Agent Purpose",
            "cost_sensitivity": "Cost Priority",
            "data_gravity":     "Data Gravity",
            "compliance_regime":"Compliance",
            "team_maturity":    "Team Maturity",
        }

        signals: list[dict] = []

        for q_key, answer_val in answers.items():
            if q_key in ("industry", "pain_points"):
                continue

            values: list[str] = answer_val if isinstance(answer_val, list) else [answer_val]

            for single_val in values:
                if not isinstance(single_val, str):
                    continue

                matched = self._match_constraint(q_key, single_val)
                if matched is None:
                    continue

                props = self.get_props(matched["id"])
                q_weight = float(props.get("weight", 0.1))
                pressures = [float(props.get(pk, 0.0)) for pk in PRESSURE_KEYS]
                contribution = pressures[axis_idx] * q_weight

                # Edge-level contributions
                for edge in self.get_out_edges(matched["id"], "PRESSURES_TOWARD"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt == pattern_id:
                        w = float((edge.get("props") or {}).get("weight", 0.5))
                        contribution += w * q_weight

                for edge in self.get_out_edges(matched["id"], "PRESSURES_AGAINST"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt == pattern_id:
                        w = float((edge.get("props") or {}).get("weight", 0.5))
                        contribution -= w * q_weight

                if abs(contribution) > 0.001:
                    if contribution > 0:
                        steers = {
                            "pattern:federated":   "Federated Platform",
                            "pattern:centralized": "Centralized Platform",
                            "pattern:mesh":        "Data Mesh",
                            "pattern:economy":     "Platform Economy",
                        }.get(pattern_id, pattern_id)
                    else:
                        # Find which pattern this signal most favors
                        best_alt = max(
                            [p for p in PATTERN_AXIS if p != pattern_id],
                            key=lambda p: pressures[PATTERN_AXIS[p]],
                            default=None,
                        )
                        steers = {
                            "pattern:federated":   "Federated Platform",
                            "pattern:centralized": "Centralized Platform",
                            "pattern:mesh":        "Data Mesh",
                            "pattern:economy":     "Platform Economy",
                        }.get(best_alt, "Other") if best_alt else "Other"

                    reason_key = (q_key, single_val.lower(), contribution > 0)
                    reason = self._SIGNAL_REASONS.get(reason_key, "")

                    signals.append({
                        "signal": _QUESTION_LABELS.get(q_key, q_key.replace("_", " ").title()),
                        "value": single_val,
                        "contribution": round(contribution, 4),
                        "direction": "positive" if contribution > 0 else "negative",
                        "steers_toward": steers,
                        "reason": reason,
                    })

        signals.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return signals[:8]

    def select_pattern(self, scores: dict[str, dict]) -> tuple[str, float]:
        """
        Return (pattern_id, confidence ∈ 0..1).
        Confidence = normalised gap between top-2 scores.
        """
        valid = {k: v for k, v in scores.items() if v["total"] > -100}
        if not valid:
            return "pattern:centralized", 0.5

        ranked = sorted(valid.items(), key=lambda x: x[1]["total"], reverse=True)
        best_id, best_val = ranked[0]
        best_total = best_val["total"]

        if len(ranked) > 1:
            second_total = ranked[1][1]["total"]
            denom = max(abs(best_total), 1.0)
            confidence = min((best_total - second_total) / denom, 1.0)
            confidence = max(confidence, 0.0)
        else:
            confidence = 1.0

        return best_id, confidence

    # ── Topology derivation (axis C — rule-based, per discovery-methodology §3.6) ──

    def derive_topology(
        self,
        pattern_id: str,
        answers: dict,
        archetype: str = "",
        pain_points: Optional[list[str]] = None,
    ) -> dict:
        """Deterministically derive the technical topology from the operating model
        (pattern_id), data location (Q5/Q6), tenancy, archetype and pain points.

        Not scored — a documented lookup. Returns:
          {base, modifiers: [...], label, rationale}
        """
        pain = [p.lower() for p in (pain_points or [])]
        lob = str(answers.get("lob_count", "")).lower()
        cloud = str(answers.get("cloud_posture", "")).lower()
        data = str(answers.get("data_gravity", "")).lower()
        tenancy = str(answers.get("tenancy_model", "")).lower()

        # ── Base topology from operating model (first match wins) ──
        if pattern_id == "pattern:centralized" and lob in ("1-3", "1", "one", ""):
            base, rationale = "single-account", "Single team on a centralized model — one account, no spokes needed."
        elif pattern_id == "pattern:centralized":
            base, rationale = "hub-and-spoke", "Centralized model with multiple teams — shared hub, thin spokes."
        elif pattern_id == "pattern:federated":
            base, rationale = "hub-and-spoke", "Federated model — shared spine (hub) with per-LOB spokes."
        elif pattern_id == "pattern:mesh":
            base, rationale = "peer-to-peer", "Mesh operating model — agents coordinate peer-to-peer (A2A)."
        elif pattern_id == "pattern:economy":
            base, rationale = "peer-to-peer", "Economy model — peer-to-peer with a marketplace control plane."
        else:
            base, rationale = "single-account", "Default single-account topology."

        # ── Modifiers (additive) ──
        modifiers: list[str] = []

        # Multi-cloud / hybrid overlay from data location or cloud posture
        if (
            "2+" in cloud or "multi" in cloud or "multi_cloud" == cloud
            or "on_prem" in cloud or "on-prem" in data or "hybrid" in data
            or "on_prem_cloud" == data
        ):
            modifiers.append("multi-cloud/hybrid")

        # Gateway-fronted for coding/customer-facing archetypes or auth/tool pains
        arche = archetype.lower()
        if (
            arche in ("coding", "coding_dev", "dev_productivity", "customer_facing", "customer-facing")
            or any(k in " ".join(pain) for k in ("auth", "tool integration", "tool fragmentation"))
        ):
            modifiers.append("gateway-fronted")

        # Account-level isolation from tenancy answer
        if "separate account" in tenancy or "account" == tenancy or "account_separated" in tenancy:
            modifiers.append("account-isolated spokes")

        label = base + ((" + " + ", ".join(modifiers)) if modifiers else "")
        return {
            "base": base,
            "modifiers": modifiers,
            "label": label,
            "rationale": rationale,
        }

    # ── Component selection ───────────────────────────────────

    # Scope of each component in a federated pattern topology.
    # "per_lob"    → each LOB/BU owns its own instance
    # "shared_spine" → single shared instance across all LOBs
    _FEDERATED_SCOPE: dict[str, str] = {
        "component:registry":      "shared_spine",
        "component:gateway":       "shared_spine",
        "component:identity":      "shared_spine",
        "component:policy_engine": "shared_spine",
        "component:observability":  "shared_spine",
        "component:cost_engine":   "shared_spine",
        "component:eval_pipeline": "shared_spine",
        "component:tool_registry": "per_lob",
        "component:memory_state":  "per_lob",
    }

    def get_components_for_pattern(
        self, pattern_id: str, answers: dict, industry: str
    ) -> list[dict]:
        """
        Return components required by the pattern, with tier elevation applied.
        Each entry: {id, name, category, layer, base_tier, final_tier, elevation_reason}
        """
        result: list[dict] = []

        for edge in self.get_out_edges(pattern_id, "REQUIRES"):
            comp_id = edge.get("to") or edge.get("target")
            comp_node = self.nodes.get(comp_id)
            if not comp_node or comp_node.get("type") != "Component":
                continue

            props = self.get_props(comp_id)
            base_tier = int(props.get("base_tier", props.get("tier", 1)))
            final_tier = base_tier
            elevation_reason: Optional[str] = None

            # Constraint elevations
            for c_node in self.get_nodes_by_type("Constraint"):
                c_props = self.get_props(c_node["id"])
                av = c_props.get("answer_value", "")
                # Check if any answer matches this constraint
                for q_val in answers.values():
                    if isinstance(q_val, str) and q_val.lower() in av.lower():
                        for elev_edge in self.get_out_edges(c_node["id"], "ELEVATES_TIER"):
                            tgt = elev_edge.get("to") or elev_edge.get("target")
                            if tgt == comp_id:
                                e_props = elev_edge.get("props", {})
                                new_tier = int(e_props.get("to_tier", final_tier + 1))
                                if new_tier > final_tier:
                                    final_tier = new_tier
                                    elevation_reason = c_props.get("answer_value", "constraint")
                        break

            # Industry tier forces
            ind_lower = industry.lower()
            for ind_node in self.get_nodes_by_type("Industry"):
                ind_props = self.get_props(ind_node["id"])
                if ind_props.get("name", "").lower() == ind_lower:
                    for ft_edge in self.get_out_edges(ind_node["id"], "FORCES_TIER"):
                        tgt = ft_edge.get("to") or ft_edge.get("target")
                        if tgt == comp_id:
                            ft_props = ft_edge.get("props", {})
                            min_t = int(ft_props.get("min_tier", final_tier))
                            if min_t > final_tier:
                                final_tier = min_t
                                elevation_reason = (elevation_reason or "") + f" [industry: {industry}]"

            result.append({
                "id": comp_id,
                "name": props.get("name", comp_id.split(":")[-1].title()),
                "category": props.get("category", "Core"),
                "layer": props.get("layer", "Shared Services"),
                "base_tier": base_tier,
                "final_tier": final_tier,
                "elevation_reason": elevation_reason,
                "aws_service": props.get("primary_aws_service", ""),
                "scope": self._FEDERATED_SCOPE.get(comp_id, "shared_spine"),
                "cost_model": props.get("cost_model"),
                "implementation": props.get("implementation"),
            })

        return result

    # ── Innovations ───────────────────────────────────────────

    def get_innovations_for_pain_points(
        self, pain_points: list[str], _pattern_id: str
    ) -> list[dict]:
        """Match pain points to Innovation nodes via SOLVES edges."""
        result: list[dict] = []
        seen: set[str] = set()

        pain_lower = [p.lower() for p in pain_points]

        def _norm_status(s: str) -> str:
            """Normalize 'current' → 'ga', keep ga/preview/emerging as-is."""
            s = s.lower()
            if s in ("ga", "current", "released"):
                return "ga"
            if s in ("preview", "beta", "limited"):
                return "preview"
            return "emerging"

        for node in self.get_nodes_by_type("Innovation"):
            nid = node["id"]
            if nid in seen:
                continue
            props = self.get_props(nid)

            # Check SOLVES edges — use edge.props.how as description (more readable)
            for edge in self.get_out_edges(nid, "SOLVES"):
                tgt = edge.get("to") or edge.get("target")
                tgt_props = self.get_props(tgt) if tgt and tgt in self.nodes else {}
                # edge 'how' is a human-readable description of what is solved
                edge_how = (edge.get("props") or {}).get("how", "")
                constraint_av = tgt_props.get("answer_value", tgt or "")
                # Match against: edge how description, constraint answer value, or
                # keywords extracted from the innovation name itself
                match_corpus = " ".join([
                    edge_how, constraint_av, props.get("name", ""), nid
                ]).lower()
                matched = any(pp in match_corpus for pp in pain_lower)
                if not matched:
                    # Expand frontend pain point labels → graph constraint vocabulary
                    _PP_EXPAND: dict[str, list[str]] = {
                        "high latency":     ["too slow", "real-time", "streaming", "token_routing"],
                        "security gaps":    ["auth", "identity", "oauth", "trust", "hallucination"],
                        "high cost":        ["too expensive", "cost", "token_routing", "intelligent"],
                        "lack of observability": ["govern/track", "govern", "track", "observab", "trace"],
                        "vendor lock":      ["framework", "portable", "mcp", "convergence"],
                        "vendor lock-in":   ["framework", "portable", "mcp", "convergence"],
                        "scaling issues":   ["at scale", "managed_agent", "event_driven"],
                        "poor governance":  ["govern", "ci/cd", "audit", "compliance"],
                        "tool fragmentation": ["silos", "tool/api", "integration", "registry"],
                        "no rag":           ["hallucination", "trust agent", "rag", "reasoning"],
                        "multi-cloud":      ["portable", "mcp", "convergence"],
                        "multi-cloud complexity": ["portable", "mcp", "convergence"],
                    }
                    # Broader keyword match: latency → token_routing, security → identity
                    keyword_map = {
                        "latency": ["token_routing", "streaming", "caching"],
                        "cost": ["token_routing", "intelligent"],
                        "security": ["identity", "oauth", "audit", "governance"],
                        "observability": ["governance", "analytics", "audit", "trace"],
                        "vendor lock": ["portable", "framework_convergence", "mcp"],
                        "rag": ["rag", "reasoning", "retrieval"],
                        "fragmentation": ["registry", "mcp", "legacy"],
                        "governance": ["governance", "compliance", "audit"],
                        "scaling": ["managed_agent", "event_driven"],
                    }
                    # Also check PP expansions against the match corpus
                    for pp in pain_lower:
                        exp_terms = _PP_EXPAND.get(pp, [])
                        if any(t in match_corpus for t in exp_terms):
                            matched = True
                            break
                    for pp in pain_lower:
                        for kw, terms in keyword_map.items():
                            if kw in pp and any(t in nid for t in terms):
                                matched = True
                                break
                        if matched:
                            break

                if matched:
                    seen.add(nid)
                    result.append({
                        "id": nid,
                        "name": props.get("name", nid.split(":")[-1]),
                        "date_emerged": props.get("date_emerged", "2024"),
                        "constraint_solved": edge_how or constraint_av or "Platform improvement",
                        "replaces": props.get("replaces"),
                        "enables": props.get("enables"),
                        "aws_implementation": props.get("aws_service", "Amazon Bedrock AgentCore"),
                        "status": _norm_status(props.get("status", "ga")),
                        "verified_via_mcp": False,
                        "enabled": True,
                    })
                    break

        # Fallback: return top innovations with sensible descriptions
        if not result:
            for node in self.get_nodes_by_type("Innovation"):
                nid = node["id"]
                props = self.get_props(nid)
                # Use first SOLVES edge 'how' as description
                first_how = ""
                for edge in self.get_out_edges(nid, "SOLVES"):
                    first_how = (edge.get("props") or {}).get("how", "")
                    if first_how:
                        break
                result.append({
                    "id": nid,
                    "name": props.get("name", nid.split(":")[-1]),
                    "date_emerged": props.get("date_emerged", "2024"),
                    "constraint_solved": first_how or "Accelerates AI platform delivery",
                    "replaces": props.get("replaces"),
                    "enables": props.get("enables"),
                    "aws_implementation": props.get("aws_service", "Amazon Bedrock AgentCore"),
                    "status": _norm_status(props.get("status", "ga")),
                    "verified_via_mcp": False,
                    "enabled": True,
                })
        return result[:8]  # cap at 8

    # ── Anti-patterns ─────────────────────────────────────────

    def get_antipatterns(
        self, _pattern_id: str, answers: dict, components: list[dict]
    ) -> list[dict]:
        """Detect triggered anti-patterns and check prevention."""
        result: list[dict] = []
        comp_ids = {c["id"] for c in components}
        tier_map = {c["id"]: c["final_tier"] for c in components}

        for node in self.get_nodes_by_type("AntiPattern"):
            nid = node["id"]
            props = self.get_props(nid)

            # Check TRIGGERED_BY edges
            triggered = False
            for edge in self.get_in_edges(nid, "TRIGGERED_BY"):
                src = edge.get("from") or edge.get("source")
                src_props = self.get_props(src) if src and src in self.nodes else {}
                av = src_props.get("answer_value", "")
                for q_val in answers.values():
                    if isinstance(q_val, str) and (
                        q_val.lower() in av.lower() or av.lower() in q_val.lower()
                    ):
                        triggered = True
                        break
                if triggered:
                    break

            if not triggered:
                continue

            # Check prevention
            prevented_by: Optional[str] = None
            for edge in self.get_in_edges(nid, "PREVENTED_BY"):
                src = edge.get("from") or edge.get("source")
                if src in comp_ids:
                    e_props = edge.get("props", {})
                    min_tier = int(e_props.get("min_tier", 1))
                    if tier_map.get(src, 0) >= min_tier:
                        comp_node = self.nodes.get(src, {})
                        prevented_by = self.get_props(src).get("name", src)
                        break

            result.append({
                "name": props.get("name", nid.split(":")[-1]),
                "severity": props.get("severity", "medium"),
                "trigger_condition": props.get("description", "See anti-pattern catalog"),
                "status": "prevented" if prevented_by else "warning",
                "prevented_by": prevented_by,
                "recommended_fix": props.get("recommended_fix"),
            })

        return result

    # ── Phasing ───────────────────────────────────────────────

    def compute_phases(self, components: list[dict]) -> list[dict]:
        """Topological sort of components into P0/P1/P2/P3 phases by tier."""
        comp_map = {c["id"]: c for c in components}

        # Build dependency graph from DEPENDS_ON edges
        deps: dict[str, set[str]] = {c["id"]: set() for c in components}
        for comp in components:
            for edge in self.get_out_edges(comp["id"], "DEPENDS_ON"):
                tgt = edge.get("to") or edge.get("target")
                if tgt in comp_map:
                    deps[comp["id"]].add(tgt)

        # Kahn's topological sort
        in_deg: dict[str, int] = {cid: 0 for cid in comp_map}
        rev_deps: dict[str, list[str]] = {cid: [] for cid in comp_map}
        for cid, dep_set in deps.items():
            for dep in dep_set:
                in_deg[cid] = in_deg.get(cid, 0) + 1
                rev_deps[dep].append(cid)

        queue = [cid for cid, d in in_deg.items() if d == 0]
        ordered: list[str] = []
        while queue:
            n = queue.pop(0)
            ordered.append(n)
            for succ in rev_deps.get(n, []):
                in_deg[succ] -= 1
                if in_deg[succ] == 0:
                    queue.append(succ)
        # Any remaining (cycles) appended last
        ordered += [cid for cid in comp_map if cid not in ordered]

        PHASE_DEFS = [
            ("P0", "Foundation (Immediate)", "Weeks 1-4"),
            ("P1", "Core Platform",          "Months 1-3"),
            ("P2", "Advanced Features",      "Months 3-6"),
            ("P3", "Autonomous Capabilities","Months 6-12"),
        ]
        phases = [{"id": p[0], "name": p[1], "duration": p[2], "components": []} for p in PHASE_DEFS]

        for cid in ordered:
            comp = comp_map.get(cid)
            if not comp:
                continue
            tier = comp.get("final_tier", 1)
            phase_idx = min(tier - 1, 3)
            phase_comp = {
                "name": comp["name"],
                "tier": tier,
                "aws_service": comp.get("aws_service", ""),
                "effort": "high" if tier == 3 else ("medium" if tier == 2 else "low"),
                "dependencies": [
                    comp_map[dep]["name"]
                    for dep in deps.get(cid, set())
                    if dep in comp_map
                ],
            }
            phases[phase_idx]["components"].append(phase_comp)

        return phases
