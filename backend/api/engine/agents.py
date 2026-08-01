"""The agentic engine: Propose → Guard → Generate → Critic.

Agents reason freely within the curated option vocabulary; the deterministic
guard (advisor_core.v3.guard) vetoes only violated constraints / fake
integrations / unbacked capabilities. Every path degrades to a deterministic
result when Bedrock is unavailable, so the endpoint always returns something
defensible.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from advisor_core.v3.guard import (
    AssertedConstraint,
    Proposal,
    ProposedComponent,
    load_bindings,
    run_guard,
)
from advisor_core.v3.models import RequirementDefinition, RequirementValueType

from . import domain
from .llm import MODEL_ID, converse, converse_json, prompt_hash

logger = logging.getLogger(__name__)

# Interfaces the platform baseline always provides. A blueprint box is one
# decision within a full platform; the surrounding baseline (identity, catalog,
# policy, telemetry, execution broker, package access...) is assumed present,
# so the integration check only fails on interfaces nothing at all provides.
BASELINE_INTERFACES = frozenset({
    "interface:audit-write", "interface:identity-assertion",
    "interface:model-catalog", "interface:policy-decision",
    "interface:quota-decision", "interface:workload-credential",
    "interface:execution-dispatch", "interface:package-retrieval",
    "interface:telemetry-ingest", "interface:model-inference",
    "interface:tool-invocation", "interface:connector-discovery",
    "interface:secret-lease",
    # provided by baseline orchestration/registry/observability platform so a
    # single-box proposal validates (the full platform supplies these):
    "interface:orchestration-control", "interface:agent-specification",
    "interface:workflow-specification", "interface:economics-record",
    "interface:evaluation-result", "interface:source-control",
})

_CATALOG_R02 = (
    Path(__file__).resolve().parents[3]
    / "PlatformAdvisorAgent" / "app" / "PlatformAdvisorAgent"
    / "advisor_core" / "v3" / "catalogs" / "coding-platform-r0.2"
)


def _known_capabilities() -> frozenset[str]:
    caps: set[str] = {SELF_HOSTED_CAP}
    for box in domain.BOXES.values():
        for opt in box.options:
            caps.update(opt.capabilities)
    return frozenset(caps)


SELF_HOSTED_CAP = "self-hosted"


def _constraints_from_answers(answers: dict) -> list[AssertedConstraint]:
    """Turn customer answers into asserted hard constraints for the guard.

    Self-hosting is forbidden via the 'self-hosted' capability token, NOT the
    component id — several options (managed and self-hosted) can map to the same
    component id, so forbidding the id would wrongly ban the managed choice too.
    """
    constraints: list[AssertedConstraint] = []
    for rule in domain.CONSTRAINT_RULES:
        if answers.get(rule.when_key) == rule.when_value:
            forbidden_caps = set(rule.forbids_capabilities)
            if rule.forbids_self_hosted:
                forbidden_caps.add(SELF_HOSTED_CAP)
            constraints.append(AssertedConstraint(
                id=rule.id,
                description=rule.description,
                forbids_capabilities=tuple(sorted(forbidden_caps)),
            ))
    return constraints


PROPOSE_SYSTEM = (
    "You are a principal cloud architect selecting services for an enterprise "
    "coding-agent platform. Choose ONE option per box from the provided menu "
    "only — never invent a service. Respect any stated constraints. Reply with "
    "JSON only: {\"selections\":[{\"box_id\":..,\"value\":..,\"reasoning\":..}]}."
)


def _propose_via_llm(answers: dict, boxes: list[str]) -> dict | None:
    menu = {
        b: {
            "question": domain.BOXES[b].question,
            "options": [{"value": o.value, "label": o.label,
                         "self_hosted": o.self_hosted} for o in domain.BOXES[b].options],
        }
        for b in boxes if b in domain.BOXES
    }
    user = (
        f"Customer answers: {json.dumps(answers)}\n\n"
        f"Decision menu (choose one value per box): {json.dumps(menu)}\n\n"
        "Return JSON only."
    )
    return converse_json(PROPOSE_SYSTEM, user, max_tokens=800)


def _deterministic_selection(answers: dict, box_id: str) -> str:
    """Fallback pick when the LLM is unavailable: first constraint-compliant option."""
    box = domain.BOXES[box_id]
    constraints = _constraints_from_answers(answers)
    forbid_self_hosted = any(
        c.forbids_component_ids or c.description for c in constraints
    ) and any(
        r.forbids_self_hosted and answers.get(r.when_key) == r.when_value
        for r in domain.CONSTRAINT_RULES
    )
    for opt in box.options:
        if forbid_self_hosted and opt.self_hosted:
            continue
        return opt.value
    return box.options[0].value


def propose(answers: dict, boxes: list[str], *, max_repropose: int = 1) -> dict:
    """Propose selections, guard them, re-propose once on veto, else fall back.

    Returns {proposal, verdict, source, prompt_hash, model_id}.
    """
    bindings = load_bindings(_CATALOG_R02)
    constraints = _constraints_from_answers(answers)
    known_caps = _known_capabilities()
    source = "agent"
    ph = ""

    def build_proposal(sel_map: dict[str, str]) -> Proposal:
        comps = []
        for box_id, value in sel_map.items():
            opt = domain.option_for(box_id, value)
            if opt is None:
                # unknown value → guard's integration check will veto
                comps.append(ProposedComponent(
                    box_id=box_id, component_id=f"component:{value}",
                ))
                continue
            alts = tuple(o.label for o in domain.BOXES[box_id].options if o.value != value)
            caps = opt.capabilities + ((SELF_HOSTED_CAP,) if opt.self_hosted else ())
            comps.append(ProposedComponent(
                box_id=box_id, component_id=opt.component_id,
                chosen_label=opt.label, alternatives=alts,
                claimed_capabilities=caps,
            ))
        # a gateway needs the model-catalog interface provider present
        return Proposal(components=tuple(comps), constraints=tuple(constraints))

    # attempt LLM proposal, then guard, then bounded re-propose, then fallback
    sel_map: dict[str, str] = {}
    llm_out = _propose_via_llm(answers, boxes)
    if llm_out and isinstance(llm_out.get("selections"), list):
        menu_user = json.dumps(answers)
        ph = prompt_hash(PROPOSE_SYSTEM, menu_user)
        for s in llm_out["selections"]:
            if isinstance(s, dict) and s.get("box_id") in domain.BOXES:
                sel_map[s["box_id"]] = str(s.get("value", ""))
    if not sel_map:
        source = "deterministic-fallback"
        sel_map = {b: _deterministic_selection(answers, b) for b in boxes if b in domain.BOXES}

    verdict = run_guard(
        build_proposal(sel_map), bindings=bindings,
        baseline_provided=BASELINE_INTERFACES, known_capabilities=known_caps,
    )

    attempts = 0
    while verdict.vetoed and attempts < max_repropose:
        attempts += 1
        # deterministic correction: drop any vetoed selection to a compliant option
        for v in verdict.violations:
            for box_id in list(sel_map):
                opt = domain.option_for(box_id, sel_map[box_id])
                if opt and opt.component_id == v.component_id:
                    sel_map[box_id] = _deterministic_selection(answers, box_id)
                    source = "agent+guard-corrected"
        verdict = run_guard(
            build_proposal(sel_map), bindings=bindings,
            baseline_provided=BASELINE_INTERFACES, known_capabilities=known_caps,
        )

    proposal = build_proposal(sel_map)
    return {
        "proposal": proposal,
        "verdict": verdict,
        "source": source,
        "prompt_hash": ph,
        "model_id": MODEL_ID,
        "cascades": _collect_cascades(sel_map),
    }


def _collect_cascades(sel_map: dict[str, str]) -> list[dict]:
    out = []
    for box_id, value in sel_map.items():
        for c in domain.cascades_for(box_id, value):
            out.append({"box_id": box_id, "value": value, "note": c.opens_note})
    return out


GENERATE_SYSTEM = (
    "You are writing the rationale section of an enterprise architecture "
    "strategy document. For each decision, explain why the chosen option beats "
    "the alternatives, in 2-3 sentences. Ground every claim in the provided "
    "reference passages; do not introduce facts not present in them. Plain, "
    "senior-architect prose. No preamble."
)


def generate(proposal: Proposal, answers: dict) -> dict:
    """Produce grounded rationale + best-practice notes from a validated proposal.

    Retrieval grounds the prose; when unavailable, emits a deterministic
    rationale from the option metadata so the output is never empty.
    """
    citations: list[dict] = []
    passages = ""
    try:
        import sys
        sys.path.insert(0, str(
            Path(__file__).resolve().parents[3]
            / "PlatformAdvisorAgent" / "app" / "PlatformAdvisorAgent"
        ))
        from pipeline_skills import kb_utils
        query = "model gateway and harness selection best practices tradeoffs " \
                + " ".join(c.chosen_label for c in proposal.components)
        hits = kb_utils.retrieve(query, top_k=4)
        passages = "\n\n---\n\n".join(h["text"] for h in hits)
        citations = [{"source": h.get("source", ""), "score": h.get("score", 0)}
                     for h in hits]
    except Exception as exc:  # noqa: BLE001
        logger.warning("KB retrieval unavailable: %s", exc)

    decisions = [
        {"box": c.box_id, "chosen": c.chosen_label,
         "alternatives": list(c.alternatives)}
        for c in proposal.components
    ]
    user = (
        f"Decisions: {json.dumps(decisions)}\n\n"
        f"Customer context: {json.dumps(answers)}\n\n"
        f"Reference passages (ground your claims in these only):\n{passages or '(none available)'}"
    )
    rationale = converse(GENERATE_SYSTEM, user, max_tokens=1000)
    grounded = bool(passages)
    if not rationale:
        rationale = _deterministic_rationale(proposal)
        grounded = False

    return {
        "rationale": rationale,
        "citations": citations,
        "grounded": grounded,
    }


def _deterministic_rationale(proposal: Proposal) -> str:
    lines = []
    for c in proposal.components:
        alts = ", ".join(c.alternatives) if c.alternatives else "the alternatives"
        lines.append(
            f"**{c.chosen_label or c.component_id}** was selected for the "
            f"{c.box_id} decision over {alts}."
        )
    return "\n\n".join(lines)


INTERPRET_SYSTEM = (
    "You are the intake interpreter for an enterprise coding-agent platform "
    "advisor. Convert the user's free-text message into structured answers the "
    "decision engine understands. Choose option values ONLY from the provided "
    "menus; infer constraint answers (operational-posture, allow-self-hosting) "
    "when the user implies them (e.g. 'no self-hosting', 'fully managed', "
    "'regulated bank'). Reply JSON only: "
    "{\"answers\":{<key>:<value>,...},\"reply\":\"<one short confirmation sentence>\"}. "
    "Only include answers you are confident about; omit the rest."
)


REQUIREMENT_INTERPRET_SYSTEM = (
    "You extract proposed requirements for an enterprise coding-agent platform. "
    "Use only requirement IDs and values from the supplied catalog. Do not make "
    "architecture or service decisions. Omit anything the user did not state or "
    "clearly imply. Reply JSON only: "
    "{\"answers\":{<requirement_id>:<catalog_value>,...},"
    "\"reply\":\"<one short proposal summary>\"}."
)


def _valid_requirement_value(
    definition: RequirementDefinition,
    value: object,
) -> bool:
    validators = {
        RequirementValueType.BOOLEAN: lambda item: isinstance(item, bool),
        RequirementValueType.INTEGER: lambda item: (
            isinstance(item, int) and not isinstance(item, bool)
        ),
        RequirementValueType.NUMBER: lambda item: (
            isinstance(item, (int, float)) and not isinstance(item, bool)
        ),
        RequirementValueType.STRING: lambda item: isinstance(item, str),
        RequirementValueType.STRING_SET: lambda item: (
            isinstance(item, list)
            and all(isinstance(member, str) for member in item)
        ),
    }
    if not validators[definition.value_type](value):
        return False
    if definition.allowed_values and value not in definition.allowed_values:
        return False
    return True


def interpret_requirements(
    message: str,
    requirements: tuple[RequirementDefinition, ...],
) -> dict:
    """Extract a catalog-constrained requirement patch without committing it."""

    menu = {
        requirement.id: {
            "name": requirement.name,
            "description": requirement.description,
            "value_type": requirement.value_type.value,
            "allowed_values": list(requirement.allowed_values),
        }
        for requirement in requirements
    }
    user = (
        f"Customer statement: {message}\n\n"
        f"Requirement catalog: {json.dumps(menu, sort_keys=True)}\n\n"
        "Return only requirements supported by the statement."
    )
    output = converse_json(REQUIREMENT_INTERPRET_SYSTEM, user, max_tokens=800)
    if not output or not isinstance(output.get("answers"), dict):
        return {
            "answers": {},
            "reply": "I could not derive a confident requirement proposal.",
            "source": "none",
        }

    definitions = {requirement.id: requirement for requirement in requirements}
    answers = {
        requirement_id: value
        for requirement_id, value in output["answers"].items()
        if requirement_id in definitions
        and _valid_requirement_value(definitions[requirement_id], value)
    }
    reply = output.get("reply")
    return {
        "answers": answers,
        "reply": (
            str(reply)
            if isinstance(reply, str) and reply.strip()
            else "I prepared a requirement proposal for review."
        ),
        "source": "agent" if answers else "none",
    }


def interpret(message: str, answers: dict) -> dict:
    """Turn a free-text chat message into typed engine answers + a short reply.

    Returns {answers: {...}, reply: str, source: 'agent'|'none'}. When Bedrock
    is unavailable it returns no answers and a graceful reply so the caller can
    fall back to click-driven input.
    """
    menu = {
        b.requirement_id: {
            "box": b.box_id,
            "question": b.question,
            "options": [{"value": o.value, "label": o.label} for o in b.options],
        }
        for b in domain.BOXES.values()
    }
    constraint_keys = {
        "operational-posture": "set to 'managed-only' if the user forbids "
                               "customer-operated infrastructure",
        "allow-self-hosting": "set to false if the user forbids self-hosting",
    }
    user = (
        f"User message: {message}\n\n"
        f"Known answers so far: {json.dumps(answers)}\n\n"
        f"Decision menus (use these requirement_id keys + option values): {json.dumps(menu)}\n\n"
        f"Constraint keys you may also set: {json.dumps(constraint_keys)}\n\n"
        "Return JSON only."
    )
    out = converse_json(INTERPRET_SYSTEM, user, max_tokens=600)
    if not out or not isinstance(out.get("answers"), dict):
        return {"answers": {}, "reply": "I couldn't interpret that — try picking "
                "an option on a block, or rephrase.", "source": "none"}
    # keep only recognised keys; coerce booleans
    valid_req = {b.requirement_id for b in domain.BOXES.values()}
    clean: dict = {}
    for k, v in out["answers"].items():
        if k in valid_req or k in constraint_keys:
            if v in ("true", "false"):
                v = v == "true"
            clean[k] = v
    return {
        "answers": clean,
        "reply": str(out.get("reply", "Got it.")),
        "source": "agent",
    }


CRITIC_SYSTEM = (
    "You are a review critic. Given a rationale and anti-pattern reference "
    "notes, list any claims that contradict the anti-patterns or overreach the "
    "evidence, as a JSON array of short strings. Empty array if clean. JSON only."
)


def critique(rationale: str) -> list[str]:
    """Re-check the rationale against anti-pattern KB; return flagged concerns."""
    try:
        import sys
        sys.path.insert(0, str(
            Path(__file__).resolve().parents[3]
            / "PlatformAdvisorAgent" / "app" / "PlatformAdvisorAgent"
        ))
        from pipeline_skills import kb_utils
        notes = kb_utils.retrieve_text("anti-patterns coding agent platform", top_k=3)
    except Exception:  # noqa: BLE001
        return []
    out = converse_json(
        CRITIC_SYSTEM,
        f"Rationale:\n{rationale}\n\nAnti-pattern notes:\n{notes}",
        max_tokens=400,
    )
    if isinstance(out, list):
        return [str(x) for x in out]
    if isinstance(out, dict) and isinstance(out.get("concerns"), list):
        return [str(x) for x in out["concerns"]]
    return []
