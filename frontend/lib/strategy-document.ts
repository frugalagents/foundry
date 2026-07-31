import type {
  ArchitectureWorkspaceProjection,
  DecisionTraceEntry,
  EvidenceClaim,
} from './architecture-workspace';

// Deterministic tech-strategy document generator.
//
// This is a pure projection of the engine's decision packet into Markdown — it
// adds no reasoning of its own, invents no facts, and calls no model. The same
// projection always yields the same document. It renders: target architecture,
// key design decisions (with the rule that fired and its cited evidence),
// best practices, and Well-Architected considerations drawn from the assurance
// packet. LLM output plays no part here.

const RELATIONSHIP_LABEL: Record<string, string> = {
  depends_on: 'depends on',
  runtime_call: 'calls',
  access_policy: 'is governed by',
};

const effectVerb: Record<string, string> = {
  require: 'requires',
  recommend: 'recommends',
  exclude: 'excludes',
};

function componentNameIndex(
  projection: ArchitectureWorkspaceProjection,
): Map<string, string> {
  const index = new Map<string, string>();
  for (const plane of projection.architecture.planes) {
    for (const component of plane.components) index.set(component.id, component.name);
  }
  return index;
}

function decisionSection(
  entries: DecisionTraceEntry[],
  names: Map<string, string>,
  evidenceById: Map<string, EvidenceClaim>,
): string[] {
  const lines: string[] = [];
  // Only components that were added by a requirement — the actual decisions.
  const decisions = entries
    .filter((e) => e.effect !== 'exclude')
    .slice()
    .sort((a, b) => a.rule_id.localeCompare(b.rule_id));
  for (const d of decisions) {
    const targets = d.target_component_ids.map((id) => names.get(id) ?? id);
    if (targets.length === 0) continue;
    lines.push(`### ${targets.join(', ')}`);
    lines.push('');
    lines.push(`- **Decision:** the platform ${effectVerb[d.effect] ?? 'requires'} ${targets.join(', ')}.`);
    lines.push(`- **Driven by:** \`${d.rule_id}\` — ${d.rationale}`);
    const claims = (d.evidence_claim_ids ?? [])
      .map((id) => evidenceById.get(id))
      .filter(Boolean) as EvidenceClaim[];
    if (claims.length > 0) {
      lines.push('- **Evidence:**');
      for (const claim of claims) {
        const src = claim.source_uri
          ? `[${claim.source_title ?? claim.source_id}](${claim.source_uri})`
          : claim.source_title ?? claim.source_id;
        lines.push(`  - ${claim.statement} — ${src}, ${claim.source_locator} (${claim.review_status}).`);
      }
    }
    lines.push('');
  }
  return lines;
}

export function buildStrategyDocument(
  projection: ArchitectureWorkspaceProjection,
): string {
  const names = componentNameIndex(projection);
  const evidenceById = new Map<string, EvidenceClaim>();
  for (const claim of projection.evidence ?? []) evidenceById.set(claim.claim_id, claim);

  const lines: string[] = [];
  lines.push(`# Coding Agent Platform — Target Architecture Strategy`);
  lines.push('');
  lines.push(`**Workspace:** ${projection.meta.workspace_name}  `);
  lines.push(`**Revision:** ${projection.meta.revision_number}  `);
  lines.push(`**Catalog:** ${projection.meta.catalog_id} ${projection.meta.catalog_version}  `);
  lines.push(`**Generated:** ${projection.meta.generated_at}`);
  lines.push('');
  lines.push('> Deterministic projection of the decision packet. Architecture, decisions, and');
  lines.push('> evidence come from the rules engine and its curated, approved evidence claims.');
  lines.push('');

  // 1. Target architecture
  lines.push('## 1. Target Architecture');
  lines.push('');
  lines.push(`Reference pattern: \`${projection.architecture.pattern_id}\` · ${projection.architecture.component_count} components · ${projection.architecture.edge_count} dependencies.`);
  lines.push('');
  for (const plane of projection.architecture.planes) {
    if (plane.components.length === 0) continue;
    lines.push(`### ${plane.label}`);
    lines.push('');
    for (const component of plane.components) {
      const tag = component.status === 'added' ? ' _(requirement-driven)_' : '';
      lines.push(`- **${component.name}**${tag} — ${component.description}`);
    }
    lines.push('');
  }

  // 2. Key design decisions
  lines.push('## 2. Key Design Decisions');
  lines.push('');
  const decisions = decisionSection(projection.decision_trace, names, evidenceById);
  if (decisions.length > 0) lines.push(...decisions);
  else {
    lines.push('_No requirement-driven decisions recorded yet._');
    lines.push('');
  }

  // 3. Best practices (from the assurance packet, deterministic)
  lines.push('## 3. Best Practices');
  lines.push('');
  const practices = projection.assurance?.security.best_practices ?? [];
  if (practices.length > 0) {
    for (const bp of practices.slice().sort((a, b) => a.practice_id.localeCompare(b.practice_id))) {
      lines.push(`- **${bp.title}** — ${bp.rationale} _(${bp.status})_`);
    }
  } else {
    lines.push('_Best-practice catalog not available for the current selection._');
  }
  lines.push('');

  // 4. Well-Architected considerations (threats + controls from assurance)
  lines.push('## 4. Well-Architected Considerations');
  lines.push('');
  const threats = projection.assurance?.security.threats ?? [];
  if (threats.length > 0) {
    lines.push('| Concern | Residual rating | Required controls |');
    lines.push('| --- | --- | --- |');
    for (const t of threats
      .slice()
      .sort((a, b) => a.threat_id.localeCompare(b.threat_id))) {
      lines.push(`| ${t.title} | ${t.residual_rating} | ${t.required_control_ids.length} |`);
    }
    lines.push('');
  } else {
    lines.push('_Security assurance packet not available for the current selection._');
    lines.push('');
  }

  return lines.join('\n');
}
