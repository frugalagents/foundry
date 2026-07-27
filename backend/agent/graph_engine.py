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

        # Build a lookup: (signal_id, answer_value) → constraint node
        # Constraint props carry both signal_id and answer_value
        # We'll iterate all constraints and match by signal_id

        # Map from app-facing question IDs to graph signal IDs
        # The graph uses Q1, Q2, … keys; our intake uses named keys.
        # We derive the mapping from the constraint nodes themselves.
        constraint_by_signal: dict[str, list[dict]] = {}
        for node in self.get_nodes_by_type("Constraint"):
            props = self.get_props(node["id"])
            sig = props.get("signal_id", "")
            constraint_by_signal.setdefault(sig, []).append(node)

        # The intake answers dict has named keys (autonomy_model, lob_count, …).
        # For each answer, find the matching constraint by answer_value text
        # OR fall back to reading pressure values from the constraint directly
        # (since graph edges carry the same information as props).

        for _q_key, answer_val in answers.items():
            if _q_key in ("industry", "pain_points"):
                continue

            # Normalise to a list so multi-select answers are each processed
            values: list[str] = answer_val if isinstance(answer_val, list) else [answer_val]

            for single_val in values:
                if not isinstance(single_val, str):
                    continue

                # Find any constraint whose answer_value matches
                matched: Optional[dict] = None
                for node in self.get_nodes_by_type("Constraint"):
                    props = self.get_props(node["id"])
                    av = props.get("answer_value", "")
                    if single_val.lower() in av.lower():
                        matched = node
                        break

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
        """Disqualify patterns blocked by Law nodes triggered by the intake answers."""
        for node in self.get_nodes_by_type("Law"):
            props = self.get_props(node["id"])
            trigger = props.get("trigger_condition", {})
            triggered = False
            if isinstance(trigger, dict):
                triggered = all(
                    str(answers.get(k, "")).lower() == str(v).lower()
                    for k, v in trigger.items()
                )
            for edge in self.get_out_edges(node["id"], "BLOCKS"):
                tgt = edge.get("to") or edge.get("target")
                if triggered and tgt in scores:
                    scores[tgt]["total"] = -999.0
        return scores

    def compute_scoring_signals(self, answers: dict, pattern_id: str) -> list[dict]:
        """Return top intake signals that drove the score for pattern_id."""
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
        }

        _ANSWER_EXPANSIONS: dict[str, list[str]] = {
            "full":           ["full autonomy", "independently"],
            "hitl":           ["humans approve", "approval gates"],
            "supervised":     ["copilot", "humans execute", "supervised"],
            "centralized":    ["centralized"],
            "federated":      ["federated"],
            "undecided":      ["undecided", "distributed"],
            "single_aws":     ["all-in on aws", "single aws"],
            "aws_primary":    ["aws-primary", "aws primary", "primary"],
            "multi_cloud":    ["2+ clouds", "multi-cloud"],
            "on_prem":        ["on-prem", "edge"],
            "open_source":    ["open-source", "open source", "oss"],
            "managed":        ["managed service", "fully managed"],
            "hybrid":         ["hybrid"],
            "single_region":  ["single", "single region"],
            "multi_region":   ["multiple", "multi-region"],
            "emerging":       ["emerging", "pilot"],
            "mature":         ["mature", "production ai"],
            "internal":       ["internal", "back-office"],
            "customer_facing":["customer-facing", "external"],
            "high":           ["high", "engineers", "dedicated"],
            "medium":         ["medium", "full-stack"],
            "low":            ["low", "no-code", "business"],
        }

        signals: list[dict] = []

        for q_key, answer_val in answers.items():
            if q_key in ("industry", "pain_points"):
                continue
            values: list = answer_val if isinstance(answer_val, list) else [answer_val]
            for single_val in values:
                if not isinstance(single_val, str):
                    continue
                search_terms = [single_val.lower()] + [
                    kw.lower() for kw in _ANSWER_EXPANSIONS.get(single_val, [])
                ]
                matched: Optional[dict] = None
                for node in self.get_nodes_by_type("Constraint"):
                    props = self.get_props(node["id"])
                    av = props.get("answer_value", "").lower()
                    if any(term in av for term in search_terms):
                        matched = node
                        break
                if matched is None:
                    continue
                props = self.get_props(matched["id"])
                q_weight = float(props.get("weight", 0.1))
                pressures = [float(props.get(pk, 0.0)) for pk in PRESSURE_KEYS]
                contribution = pressures[axis_idx] * q_weight
                for edge in self.get_out_edges(matched["id"], "PRESSURES_TOWARD"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt == pattern_id:
                        contribution += float((edge.get("props") or {}).get("weight", 0.5)) * q_weight
                for edge in self.get_out_edges(matched["id"], "PRESSURES_AGAINST"):
                    tgt = edge.get("to") or edge.get("target")
                    if tgt == pattern_id:
                        contribution -= float((edge.get("props") or {}).get("weight", 0.5)) * q_weight
                if abs(contribution) > 0.001:
                    _PATTERN_NAMES = {
                        "pattern:federated":   "Federated Platform",
                        "pattern:centralized": "Centralized Platform",
                        "pattern:mesh":        "Data Mesh",
                        "pattern:economy":     "Platform Economy",
                    }
                    if contribution > 0:
                        steers = _PATTERN_NAMES.get(pattern_id, pattern_id)
                    else:
                        pressures_local = [float(self.get_props(matched["id"]).get(pk, 0.0)) for pk in PRESSURE_KEYS]
                        best_alt = max(
                            [p for p in PATTERN_AXIS if p != pattern_id],
                            key=lambda p: pressures_local[PATTERN_AXIS[p]],
                            default=None,
                        )
                        steers = _PATTERN_NAMES.get(best_alt, "Other") if best_alt else "Other"

                    signals.append({
                        "signal": _QUESTION_LABELS.get(q_key, q_key.replace("_", " ").title()),
                        "value": single_val,
                        "contribution": round(contribution, 4),
                        "direction": "positive" if contribution > 0 else "negative",
                        "steers_toward": steers,
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

    # ── Component selection ───────────────────────────────────

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
        Each entry: {id, name, category, layer, base_tier, final_tier, elevation_reason, scope}
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

        for node in self.get_nodes_by_type("Innovation"):
            nid = node["id"]
            if nid in seen:
                continue
            props = self.get_props(nid)

            # Check SOLVES edges
            for edge in self.get_out_edges(nid, "SOLVES"):
                tgt = edge.get("to") or edge.get("target")
                tgt_props = self.get_props(tgt) if tgt and tgt in self.nodes else {}
                solved_str = tgt_props.get("answer_value", tgt or "")
                if any(pp in solved_str.lower() or solved_str.lower() in pp for pp in pain_lower):
                    seen.add(nid)
                    result.append({
                        "id": nid,
                        "name": props.get("name", nid.split(":")[-1]),
                        "date_emerged": props.get("date_emerged", "2024"),
                        "constraint_solved": solved_str,
                        "replaces": props.get("replaces"),
                        "enables": props.get("enables"),
                        "aws_implementation": props.get("aws_service", "Amazon Bedrock"),
                        "status": props.get("status", "ga"),
                        "verified_via_mcp": False,
                        "enabled": True,
                    })
                    break

        # Also return all innovations if pain_points is broad
        if not result:
            for node in self.get_nodes_by_type("Innovation"):
                props = self.get_props(node["id"])
                result.append({
                    "id": node["id"],
                    "name": props.get("name", node["id"].split(":")[-1]),
                    "date_emerged": props.get("date_emerged", "2024"),
                    "constraint_solved": "General platform improvement",
                    "replaces": props.get("replaces"),
                    "enables": props.get("enables"),
                    "aws_implementation": props.get("aws_service", "Amazon Bedrock"),
                    "status": props.get("status", "ga"),
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
