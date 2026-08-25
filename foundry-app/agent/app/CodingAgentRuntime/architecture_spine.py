from __future__ import annotations

from typing import Any, Mapping


def build_architecture_snapshot(workspace: Mapping[str, Any] | None) -> dict[str, Any] | None:
    workspace = workspace or {}
    fact_map = _fact_map(workspace)
    decision_paths = _decision_paths(workspace)
    if not _has_minimum_details(workspace, fact_map):
        return None

    operating_model = str(workspace.get("operating_model") or "undecided").strip() or "undecided"
    current_tools = _current_tools(fact_map)
    export_control = bool(fact_map.get("export_control"))
    local_execution_requested = bool(fact_map.get("local_execution_requested"))
    local_execution_scope = str(fact_map.get("local_execution_scope") or "").strip()
    regulated_isolated = bool(fact_map.get("regulated_population_isolated"))
    central_identity_broker = "decision/identity-boundary/central-broker" in decision_paths
    shared_control_plane = any(path.startswith("decision/control-plane/shared-") for path in decision_paths)
    shared_model_gateway = any(path.startswith("decision/model-routing/shared-gateway") for path in decision_paths)
    tiered_model_routing = "decision/model-routing/shared-gateway-tiered" in decision_paths
    federated_multi_cloud = "decision/multi-cloud/federated-governed-lanes" in decision_paths

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    surface_nodes = [
        _node("surface-entry", _surface_label(current_tools), _surface_sublabel(current_tools), "monitor", "#5161ff", "surface", "developer_surface"),
    ]
    harness_nodes = [
        _node("harness-model", _harness_label(operating_model), _harness_sublabel(operating_model, current_tools), "blocks", "#7c4dff", "harness", "harness"),
    ]
    execution_nodes = [
        _node("execution-main", _execution_label(local_execution_requested, local_execution_scope), _execution_sublabel(local_execution_requested, local_execution_scope), "container", "#a855f7", "execution", "agent_runtime"),
    ]
    baseline_nodes = [
        *surface_nodes,
        *harness_nodes,
        *execution_nodes,
        _node("gateway-tools", "Tool / MCP gateway", "Enterprise tool access path", "plug", "#0ea5e9", "gateway", "tool_gateway"),
        _node("gateway-model", _model_gateway_label(shared_model_gateway), _model_gateway_sublabel(shared_model_gateway, shared_control_plane), "split", "#0ea5e9", "gateway", "model_gateway"),
        _node("model-route", _model_route_label(shared_model_gateway, tiered_model_routing), _model_route_sublabel(shared_model_gateway, tiered_model_routing), "brain", "#10b981", "model", "model_provider"),
        _node("access-identity", _identity_label(central_identity_broker), _identity_sublabel(central_identity_broker), "lock", "#ef4444", "access", "identity_control", path_role="overlay"),
        _node("access-policy", "Guardrails / policy", _policy_sublabel(shared_control_plane), "shield-alert", "#ef4444", "access", "policy_control", path_role="overlay"),
        _node("access-quota", "Quota / spend control", _quota_sublabel(shared_control_plane), "coins", "#ef4444", "access", "quota_control", path_role="overlay"),
        _node("ops-observability", "Observability / audit", "Traceability and evidence trail", "radar", "#f59e0b", "ops", "audit_ops", path_role="overlay"),
    ]
    nodes.extend(baseline_nodes)

    main_flow_ids = [
        "surface-entry",
        "harness-model",
        "execution-main",
        "gateway-tools",
        "gateway-model",
        "model-route",
    ]
    for source, target in zip(main_flow_ids, main_flow_ids[1:]):
        edges.append(_edge(source, target))

    edges.extend(
        [
            _edge("access-identity", "harness-model", dashed=True, color="#ef4444"),
            _edge("access-policy", "execution-main", dashed=True, color="#ef4444"),
            _edge("access-quota", "gateway-model", dashed=True, color="#ef4444"),
            _edge("ops-observability", "gateway-tools", dashed=True, color="#f59e0b"),
        ]
    )

    customizations: list[dict[str, Any]] = []
    supporting_lanes: list[dict[str, Any]] = []
    added_node_ids: list[str] = []

    estate_harness_nodes = _tool_harness_nodes(current_tools, operating_model, path_role="supporting")
    if estate_harness_nodes:
        nodes.extend(estate_harness_nodes)
        estate_harness_ids = [node["id"] for node in estate_harness_nodes]
        for node_id in estate_harness_ids:
            edges.append(_edge("harness-model", node_id, dashed=True, color="#7c4dff"))
        supporting_lanes.append(
            {
                "id": "current-estate-harnesses",
                "title": _estate_lane_title(operating_model),
                "narrative": _estate_lane_narrative(operating_model, current_tools),
                "component_ids": estate_harness_ids,
            }
        )

    if export_control:
        nodes.append(
            _node(
                "execution-regulated",
                "MicroVM runtime",
                "Isolated execution lane for export-controlled workloads",
                "server-cog",
                "#a855f7",
                "execution",
                "regulated_execution",
                path_role="supporting",
            )
        )
        nodes.append(
            _node(
                "access-export-control",
                "Export-control boundary",
                "Session gating for regulated repos",
                "flag",
                "#ef4444",
                "access",
                "compliance_control",
                path_role="overlay",
            )
        )
        edges.extend(
            [
                _edge("harness-model", "execution-regulated", dashed=True, color="#7c4dff"),
                _edge("access-export-control", "execution-regulated", dashed=True, color="#ef4444"),
                _edge("ops-observability", "execution-regulated", dashed=True, color="#f59e0b"),
            ]
        )
        added_node_ids.extend(["execution-regulated", "access-export-control"])
        customizations.append(
            {
                "id": "regulated-lane",
                "title": "Dedicated regulated lane",
                "layer": "execution",
                "added_component_ids": ["execution-regulated", "access-export-control"],
                "reason": "Export-controlled workloads require a separate execution and policy boundary from the general developer default path.",
                "tradeoff": "Adds platform complexity, but avoids treating a hard regulatory boundary as a soft workflow preference.",
                "triggered_by": ["export control in scope"],
            }
        )
        supporting_lanes.append(
            {
                "id": "regulated-supporting-lane",
                "title": "Regulated execution lane",
                "narrative": "Sensitive workloads are kept on a separate execution and control path instead of riding the general developer default lane.",
                "component_ids": ["execution-regulated", "access-export-control"],
            }
        )

    if local_execution_requested and local_execution_scope == "non_regulated_only":
        nodes.append(
            _node(
                "execution-local-general",
                "Local execution",
                "Limited to non-regulated repo classes",
                "laptop",
                "#a855f7",
                "execution",
                "local_execution_lane",
                path_role="supporting",
            )
        )
        edges.append(_edge("harness-model", "execution-local-general", dashed=True, color="#7c4dff"))
        edges.append(_edge("access-policy", "execution-local-general", dashed=True, color="#ef4444"))
        added_node_ids.append("execution-local-general")
        customizations.append(
            {
                "id": "local-general-lane",
                "title": "Scoped local execution lane",
                "layer": "execution",
                "added_component_ids": ["execution-local-general"],
                "reason": "Local execution is allowed only for lower-sensitivity workflows rather than as a shared default for all repo classes.",
                "tradeoff": "Improves developer convenience for general workflows, but requires clear repo classification and routing discipline.",
                "triggered_by": ["local execution request", "non-regulated scope only"],
            }
        )
        supporting_lanes.append(
            {
                "id": "local-general-lane-support",
                "title": "Local execution for general workflows",
                "narrative": "A narrower local lane exists for non-regulated work while sensitive workloads stay on a separate controlled path.",
                "component_ids": ["execution-local-general"],
            }
        )

    if operating_model in {"multi_harness_governed", "default_plus_exceptions"}:
        nodes.append(
            _node(
                "access-exception-governance",
                "Exception governance",
                "Population mapping and review path",
                "users",
                "#ef4444",
                "access",
                "exception_control",
                path_role="overlay",
            )
        )
        edges.append(_edge("access-exception-governance", "harness-model", dashed=True, color="#ef4444"))
        added_node_ids.append("access-exception-governance")
        customizations.append(
            {
                "id": "exception-governance",
                "title": "Explicit exception governance",
                "layer": "access",
                "added_component_ids": ["access-exception-governance"],
                "reason": "The target operating model relies on governed populations and exception boundaries rather than one universal default path.",
                "tradeoff": "Adds governance overhead, but avoids shadow standards and unmanaged tool sprawl.",
                "triggered_by": [operating_model.replace("_", " ")],
            }
        )

    if federated_multi_cloud:
        nodes.append(
            _node(
                "ops-federated-cloud-lane",
                "Federated cloud lane",
                "Azure or GCP populations stay cloud-resident under the same audit and policy canon",
                "cloud",
                "#f59e0b",
                "ops",
                "federated_lane",
                path_role="supporting",
            )
        )
        edges.append(_edge("ops-observability", "ops-federated-cloud-lane", dashed=True, color="#f59e0b"))
        customizations.append(
            {
                "id": "federated-cloud-lane",
                "title": "Federated cloud-resident lane",
                "layer": "ops",
                "added_component_ids": ["ops-federated-cloud-lane"],
                "reason": "A durable Azure or GCP footprint is being governed as part of the target platform instead of treated as a temporary migration exception.",
                "tradeoff": "Preserves governance parity across clouds, but requires consistent identity and evidence handling beyond one AWS-native instance.",
                "triggered_by": ["federated multi-cloud governance"],
            }
        )
        supporting_lanes.append(
            {
                "id": "federated-cloud-lane-support",
                "title": "Federated cloud-resident lane",
                "narrative": "Non-AWS populations remain on their cloud footprint, but stay under the same identity, policy, and audit model.",
                "component_ids": ["ops-federated-cloud-lane"],
            }
        )

    baseline_node_ids = [node["id"] for node in baseline_nodes]
    architecture_artifact = {
        "executive_summary": _executive_summary(
            operating_model=operating_model,
            current_tools=current_tools,
            export_control=export_control,
            local_execution_requested=local_execution_requested,
            regulated_isolated=regulated_isolated,
            shared_model_gateway=shared_model_gateway,
            central_identity_broker=central_identity_broker,
        ),
        "baseline": {
            "name": "Working enterprise baseline",
            "layers": _baseline_layers(nodes, baseline_node_ids),
        },
        "customizations": customizations,
        "decisions": _decision_entries(workspace),
        "risks": _risk_entries(workspace),
        "rollout": _rollout_entries(export_control, local_execution_requested),
        "primary_flow": [
            {
                "id": "primary-request-path",
                "title": "Primary request path",
                "narrative": "Developer requests enter through the approved surface, run through the harness and execution boundary, then reach enterprise tool and model routing.",
                "component_ids": main_flow_ids,
            }
        ],
        "cross_cutting_controls": [
            {
                "id": "identity-access",
                "title": "Identity and access controls",
                "narrative": "Corporate identity, policy enforcement, and spend controls apply across every request path rather than inside a single box.",
                "component_ids": ["access-identity", "access-policy", "access-quota"],
            },
            {
                "id": "audit-observability",
                "title": "Observability and audit",
                "narrative": "Every lane feeds a shared audit and observability model so the platform can trace actions and enforce evidence requirements.",
                "component_ids": ["ops-observability"],
            },
        ],
        "supporting_lanes": supporting_lanes,
    }

    return {
        "stage": "baseline",
        "nodes": nodes,
        "edges": edges,
        "baseline_node_ids": baseline_node_ids,
        "architecture_artifact": architecture_artifact,
    }


def _has_minimum_details(workspace: Mapping[str, Any], fact_map: Mapping[str, Any]) -> bool:
    facts = workspace.get("facts") if isinstance(workspace.get("facts"), list) else []
    context = bool(fact_map.get("current_tools")) or bool(fact_map.get("local_execution_requested")) or str(workspace.get("operating_model") or "") not in {"", "undecided"}
    constraint = bool(fact_map.get("export_control")) or bool(fact_map.get("regulated_population_isolated")) or bool(fact_map.get("local_execution_scope"))
    direction = bool(str(workspace.get("recommendation") or "").strip()) or bool(workspace.get("question_state")) or bool(workspace.get("decisions"))
    return direction and ((context and constraint) or len(facts) >= 3)


def _fact_map(workspace: Mapping[str, Any]) -> dict[str, Any]:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = (
        traversal_state.get("customer_confirmed_facts")
        if isinstance(traversal_state.get("customer_confirmed_facts"), list)
        else traversal_state.get("structured_facts")
        if isinstance(traversal_state.get("structured_facts"), list)
        else []
    )
    fact_map: dict[str, Any] = {}
    if isinstance(structured, list):
        for item in structured:
            if not isinstance(item, Mapping):
                continue
            source = str(item.get("source") or "").strip().lower()
            if source and source not in {"customer", "customer_confirmed", "explicit_constraint", "operating_model"}:
                continue
            key = str(item.get("key") or "").strip()
            if key:
                fact_map[key] = item.get("value")
    operating_model = str(workspace.get("operating_model") or "").strip()
    if operating_model and operating_model != "undecided":
        fact_map["operating_model"] = operating_model
    return fact_map


def _node(
    node_id: str,
    label: str,
    sublabel: str,
    icon: str,
    color: str,
    layer: str,
    kind: str,
    *,
    path_role: str = "primary",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "arch",
        "label": label,
        "sublabel": sublabel,
        "icon": icon,
        "color": color,
        "x": 0,
        "y": 0,
        "layer": layer,
        "kind": kind,
        "path_role": path_role,
    }


def _edge(source: str, target: str, *, dashed: bool = False, color: str | None = None) -> dict[str, Any]:
    return {
        "id": f"{source}->{target}",
        "source": source,
        "target": target,
        "dashed": dashed,
        "color": color,
    }


def _harness_label(operating_model: str) -> str:
    if operating_model == "single_standard":
        return "Single standard harness"
    if operating_model == "multi_harness_governed":
        return "Governed harness portfolio"
    if operating_model == "default_plus_exceptions":
        return "Default harness lane [TBD]"
    return "Target-state harness policy [TBD]"


def _harness_sublabel(operating_model: str, current_tools: list[str]) -> str:
    if operating_model == "single_standard":
        return "One governed default path for the main developer population."
    if operating_model == "multi_harness_governed":
        return "Approved harnesses operate under one shared identity, policy, audit, and gateway model."
    if operating_model == "default_plus_exceptions":
        return "One default path with explicit exception governance, but the default tool has not been locked yet."
    return "Current tool sprawl is being converted into a governed target-state harness model."


def _execution_label(local_execution_requested: bool, local_execution_scope: str) -> str:
    if local_execution_requested and local_execution_scope == "non_regulated_only":
        return "Container runtime"
    if local_execution_requested:
        return "Container runtime [under review]"
    return "Container runtime"


def _execution_sublabel(local_execution_requested: bool, local_execution_scope: str) -> str:
    if local_execution_requested and local_execution_scope == "non_regulated_only":
        return "Controlled default runtime for governed repos while approved local lanes stay separate"
    if local_execution_requested:
        return "Local execution is in play, but the safe default runtime boundary is still being resolved"
    return "Controlled default runtime for the approved harness model"


def _baseline_layers(nodes: list[dict[str, Any]], baseline_node_ids: list[str]) -> list[dict[str, Any]]:
    baseline_set = set(baseline_node_ids)
    layer_order = [
        ("surface", "Surface", "How developers enter and use the platform."),
        ("harness", "Harness", "The governed working environment the enterprise supports."),
        ("execution", "Execution", "Where agent-driven actions run and the trust boundary that contains them."),
        ("gateway", "Gateway", "The shared routing and broker layer for tools and models."),
        ("model", "Model", "The approved provider and tiering route."),
        ("access", "Control plane", "Identity, policy, and quota controls applied across the stack."),
        ("ops", "Observability", "Tracing, evidence, and audit operations for the platform."),
    ]
    layers: list[dict[str, Any]] = []
    for layer_id, label, purpose in layer_order:
        layer_nodes = [node for node in nodes if node["id"] in baseline_set and node.get("layer") == layer_id]
        layers.append(
            {
                "id": layer_id,
                "label": label,
                "purpose": purpose,
                "component_ids": [node["id"] for node in layer_nodes],
                "component_labels": [node["label"] for node in layer_nodes],
            }
        )
    return layers


def _decision_entries(workspace: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    candidate_options = []
    traversal_state = workspace.get("traversal_state")
    if isinstance(traversal_state, Mapping) and isinstance(traversal_state.get("candidate_options"), list):
        candidate_options = traversal_state.get("candidate_options") or []
    rejected = [
        str(item.get("title") or "").strip()
        for item in candidate_options
        if isinstance(item, Mapping) and str(item.get("position") or "").strip() in {"viable", "deferred"}
    ]
    for decision in _string_list(workspace.get("decisions"))[:4]:
        entries.append(
            {
                "decision": decision,
                "why": "Derived from the current customer facts and the active OKF decision path.",
                "alternatives_rejected": rejected[:2],
            }
        )
    if not entries and str(workspace.get("recommendation") or "").strip():
        entries.append(
            {
                "decision": str(workspace.get("recommendation") or "").strip(),
                "why": "This is the current working architecture direction while remaining blockers are being resolved.",
                "alternatives_rejected": rejected[:2],
            }
        )
    return entries


def _risk_entries(workspace: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "risk": risk,
            "mitigation": "Resolve the active blocker and refresh the architecture once the boundary is explicit.",
        }
        for risk in _string_list(workspace.get("risks"))[:4]
    ]


def _rollout_entries(export_control: bool, local_execution_requested: bool) -> list[dict[str, Any]]:
    entries = [
        {
            "phase": "Baseline architecture",
            "outcome": "Establish a single governed target-state shape with explicit open boundaries instead of leaving the platform as a product shortlist.",
        }
    ]
    if export_control:
        entries.append(
            {
                "phase": "Regulated lane confirmation",
                "outcome": "Lock the regulated execution and identity boundary before broadening rollout beyond general engineering workflows.",
            }
        )
    if local_execution_requested:
        entries.append(
            {
                "phase": "Execution policy shaping",
                "outcome": "Decide which repo classes and populations may use local execution versus the controlled default path.",
            }
        )
    return entries


def _executive_summary(
    *,
    operating_model: str,
    current_tools: list[str],
    export_control: bool,
    local_execution_requested: bool,
    regulated_isolated: bool,
    shared_model_gateway: bool,
    central_identity_broker: bool,
) -> str:
    model_text = {
        "single_standard": "one standard harness path",
        "multi_harness_governed": "a governed harness portfolio",
        "default_plus_exceptions": "one default harness with formal exception lanes",
    }.get(operating_model, "a governed target-state harness model still being finalized")

    tools_text = f" Current tools in scope include {', '.join(current_tools[:3])}." if current_tools else ""
    gateway_text = "shared tool and model gateways" if shared_model_gateway else "shared tool access plus a model boundary still being finalized"
    identity_text = "a brokered identity boundary" if central_identity_broker else "a cross-cutting identity boundary"
    summary = f"The current working architecture assumes {model_text}, routed through {gateway_text} with {identity_text}, policy, quota, and audit controls applied across every lane.{tools_text}"
    if export_control and not regulated_isolated:
        summary += " Export-controlled workloads are forcing a separate regulated runtime decision before the execution model can be finalized."
    elif export_control and regulated_isolated:
        summary += " Export-controlled workloads are carved into a separate microVM-style controlled lane rather than treated as part of the general developer default path."
    if local_execution_requested:
        summary += " Local execution remains scoped and governed rather than becoming the universal default without a repo-class boundary."
    return summary


def _decision_paths(workspace: Mapping[str, Any]) -> set[str]:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    paths: set[str] = set()
    active_slice = traversal_state.get("active_slice") if isinstance(traversal_state.get("active_slice"), Mapping) else {}
    active_decision = traversal_state.get("active_decision") if isinstance(traversal_state.get("active_decision"), Mapping) else {}
    for item in (active_slice, active_decision):
        path = str(item.get("path") or "").strip()
        if path:
            paths.add(path)
    for path in traversal_state.get("selected_node_paths", []):
        if isinstance(path, str) and path.strip():
            paths.add(path.strip())
    candidate_options = traversal_state.get("candidate_options") if isinstance(traversal_state.get("candidate_options"), list) else []
    for item in candidate_options:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or "").strip()
        position = str(item.get("position") or "").strip()
        if path and position in {"recommended", "selected", "viable"}:
            paths.add(path)
    return paths


def _model_gateway_label(shared_model_gateway: bool) -> str:
    return "Shared model gateway" if shared_model_gateway else "Model gateway"


def _model_gateway_sublabel(shared_model_gateway: bool, shared_control_plane: bool) -> str:
    if shared_model_gateway:
        return "All approved harnesses reach providers through one governed routing boundary"
    if shared_control_plane:
        return "Provider access is expected to stay centralized, but the shared routing policy is still being finalized"
    return "Routing and provider policy"


def _model_route_label(shared_model_gateway: bool, tiered_model_routing: bool) -> str:
    if tiered_model_routing:
        return "Tiered provider routing"
    if shared_model_gateway:
        return "Shared provider route"
    return "Approved model route [TBD]"


def _model_route_sublabel(shared_model_gateway: bool, tiered_model_routing: bool) -> str:
    if tiered_model_routing:
        return "Cheaper and frontier models are selected deliberately by task shape behind one gateway"
    if shared_model_gateway:
        return "One governed provider route is expected, but tiering policy is still being finalized"
    return "Provider and tier policy still needs a final enterprise decision"


def _identity_label(central_identity_broker: bool) -> str:
    return "Identity broker" if central_identity_broker else "Identity"


def _identity_sublabel(central_identity_broker: bool) -> str:
    if central_identity_broker:
        return "One broker normalizes claims across upstream IdPs before platform access is granted"
    return "Corporate auth and session identity"


def _policy_sublabel(shared_control_plane: bool) -> str:
    if shared_control_plane:
        return "Usage policy, DLP, and approval controls stay shared across every approved lane"
    return "Usage policy and DLP controls"


def _quota_sublabel(shared_control_plane: bool) -> str:
    if shared_control_plane:
        return "Spend ceilings and attribution stay on the shared control plane even when lanes differ"
    return "Usage ceilings and attribution"


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _current_tools(fact_map: Mapping[str, Any]) -> list[str]:
    raw = fact_map.get("current_tools")
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    tools: list[str] = []
    for item in raw:
        tool = str(item).strip()
        key = tool.lower()
        if not tool or key in seen:
            continue
        seen.add(key)
        tools.append(tool)
    return tools


def _surface_label(current_tools: list[str]) -> str:
    lowered = " ".join(tool.lower() for tool in current_tools)
    if any(token in lowered for token in ("cursor", "copilot", "ide")):
        return "IDE surfaces"
    if any(token in lowered for token in ("cli", "claude code", "codex")):
        return "CLI surfaces"
    return "Developer surfaces"


def _surface_sublabel(current_tools: list[str]) -> str:
    if current_tools:
        return f"Entry points currently in scope: {', '.join(current_tools[:3])}"
    return "IDE / CLI entry points"


def _tool_harness_nodes(current_tools: list[str], operating_model: str, *, path_role: str = "primary") -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for tool in current_tools[:4]:
        label, icon = _tool_label_and_icon(tool)
        nodes.append(
            _node(
                f"harness-{_slug(tool)}",
                label,
                _tool_harness_sublabel(label, operating_model),
                icon,
                "#7c4dff",
                "harness",
                "interactive_harness",
                path_role=path_role,
            )
        )
    return nodes


def _tool_harness_sublabel(tool: str, operating_model: str) -> str:
    if operating_model == "multi_harness_governed":
        return f"{tool} is part of the current estate and may remain as a governed portfolio member once explicitly confirmed"
    if operating_model == "default_plus_exceptions":
        return f"{tool} is in the current estate and must be classified as default, exception-only, or retired"
    if operating_model == "single_standard":
        return f"{tool} is in the current estate and must either map to the single standard or be retired"
    return f"{tool} is in the current estate and informs the target-state harness choice"


def _estate_lane_title(operating_model: str) -> str:
    if operating_model == "multi_harness_governed":
        return "Estate harnesses under portfolio confirmation"
    if operating_model == "default_plus_exceptions":
        return "Estate harnesses under default-versus-exception review"
    if operating_model == "single_standard":
        return "Estate harnesses to rationalize"
    return "Current estate harnesses in scope"


def _estate_lane_narrative(operating_model: str, current_tools: list[str]) -> str:
    estate = ", ".join(current_tools[:4])
    if operating_model == "multi_harness_governed":
        return f"{estate} are present in the current estate, but the target-state approved portfolio still needs explicit confirmation rather than being assumed from today’s tool mix."
    if operating_model == "default_plus_exceptions":
        return f"{estate} are in the current estate, but they are shown as context until the platform decides which tool is default, which are exception-only, and which should retire."
    if operating_model == "single_standard":
        return f"{estate} are in the current estate and need a migration or retirement path so the target state can converge on one governed default harness."
    return f"{estate} are current-state inputs to the architecture decision, not implicit target-state approvals."


def _tool_label_and_icon(tool: str) -> tuple[str, str]:
    normalized = tool.strip().lower()
    if normalized == "cursor":
        return "Cursor", "mouse-pointer-2"
    if normalized in {"github copilot", "copilot"}:
        return "GitHub Copilot", "sparkles"
    if normalized == "claude code":
        return "Claude Code", "terminal"
    if normalized == "codex cli":
        return "Codex CLI", "terminal-square"
    return tool.strip(), "blocks"


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
