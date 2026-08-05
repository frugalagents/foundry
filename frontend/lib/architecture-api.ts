import { getAccessToken, refreshIdToken } from './auth';
import type {
  AnswerEnrichment,
  ArchitectureWorkspaceProjection,
  RequirementStatus,
  RequirementValue,
} from './architecture-workspace';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080/api/v1';
type JsonObject = Record<string, unknown>;

export interface ArchitectureWorkspaceScope {
  customer_id: string;
  session_id: string;
}

export class ArchitectureApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(`Architecture API ${status}`);
    this.name = 'ArchitectureApiError';
  }
}

const scopedPath = (path: string, scope?: ArchitectureWorkspaceScope): string => {
  if (!scope) return path;
  const params = new URLSearchParams({
    customer_id: scope.customer_id,
    session_id: scope.session_id,
  });
  return `${path}?${params.toString()}`;
};

const object = (value: unknown) => value as JsonObject;
const refs = (items: unknown, key: string): string[] =>
  ((items as JsonObject[]) ?? []).map((item) => String(item[key]));
const requirementStatus = (value: unknown): RequirementStatus => {
  if (value === 'answered' || value === 'unknown' || value === 'unanswered') {
    return value;
  }
  if (value === 'assumed') return value;
  return 'unanswered';
};

export function normalizeArchitectureProjection(input: unknown): ArchitectureWorkspaceProjection {
  const raw = object(input);
  const workspace = object(raw.workspace);
  const catalog = object(raw.catalog);
  const revision = object(raw.revision);
  const architecture = object(raw.architecture);
  const pattern = object(architecture.pattern);
  const summary = object(architecture.summary);

  return {
    meta: {
      workspace_id: String(workspace.workspace_id),
      workspace_name: 'Enterprise coding agent platform',
      revision_id: String(revision.revision_id),
      revision_number: Number(revision.revision_number),
      catalog_id: String(catalog.catalog_release_id),
      catalog_version: String(catalog.version),
      generated_at: String(revision.created_at),
      persistence_revision: workspace.persistence_revision
        ? Number(workspace.persistence_revision)
        : undefined,
      persistence_hash: workspace.persistence_hash
        ? String(workspace.persistence_hash)
        : undefined,
    },
    requirements: (raw.requirements as JsonObject[]).map((item) => ({
      id: String(item.requirement_id),
      name: String(item.name),
      description: item.description ? String(item.description) : undefined,
      customer_question: item.customer_question ? String(item.customer_question) : undefined,
      why_it_matters: item.why_it_matters ? String(item.why_it_matters) : undefined,
      candidate_answers: item.candidate_answers as RequirementValue[] | undefined,
      required: Boolean(item.required),
      value: item.value as RequirementValue,
      status: requirementStatus(item.status),
      source: item.source ? String(item.source) : undefined,
      assumption: item.assumption
        ? object(item.assumption) as unknown as {
          rationale: string;
          confidence: number;
          owner: string;
          source: string;
        }
        : undefined,
    })),
    assumptions: (raw.assumptions as ArchitectureWorkspaceProjection['assumptions']) ?? [],
    architecture: {
      pattern_id: String(pattern.pattern_id),
      component_count: Number(summary.current_component_count),
      edge_count: Number(summary.current_edge_count),
      planes: (architecture.planes as JsonObject[]).map((plane) => ({
        id: String(plane.plane_id),
        label: String(plane.name),
        components: (plane.components as JsonObject[]).map((component) => ({
          id: String(component.component_id),
          name: String(component.name),
          description: String(component.description),
          kind: String(component.kind),
          status: String(component.status) as 'baseline' | 'added',
        })),
      })),
      edges: (architecture.edges as JsonObject[]).map((edge) => ({
        id: String(edge.edge_id),
        source_component_id: String(object(edge.source).component_id),
        target_component_id: String(object(edge.target).component_id),
        relationship: String(edge.relationship),
      })),
    },
    feasibility: (raw.deployment_families as JsonObject[]).map((family) => ({
      pattern_id: String(family.pattern_id),
      name: String(family.name),
      description: family.description ? String(family.description) : undefined,
      reason: family.reason ? String(family.reason) : undefined,
      status: String(family.status) as 'feasible' | 'rejected' | 'unknown',
      rejection_rule_ids: family.rejection_rule_ids as string[],
      blocking_requirement_ids: refs(family.blocking_requirements, 'requirement_id'),
    })),
    deployable_solution: raw.deployable_solution as ArchitectureWorkspaceProjection['deployable_solution'],
    assurance: raw.assurance as ArchitectureWorkspaceProjection['assurance'],
    next_question: raw.next_question ? (() => {
      const question = object(raw.next_question);
      return {
        requirement_id: String(question.requirement_id),
        prompt: String(question.prompt),
        customer_question: question.customer_question ? String(question.customer_question) : String(question.prompt),
        why_it_matters: question.why_it_matters ? String(question.why_it_matters) : undefined,
        why_now: String(question.why_now),
        candidate_answers: question.candidate_answers as RequirementValue[],
        answer_enrichments: ((question.answer_enrichments as (JsonObject | null)[]) ?? []).map((e) =>
          e ? {
            label: String(e.label ?? ''),
            description: String(e.description ?? ''),
            best_for: e.best_for ? String(e.best_for) : undefined,
            watch_out: e.watch_out ? String(e.watch_out) : undefined,
          } as AnswerEnrichment : null,
        ),
        answer_impacts: ((question.answer_impacts as JsonObject[]) ?? []).map((impact) => {
          const components = impact.components ? object(impact.components) : {} as JsonObject;
          const edges = impact.edges ? object(impact.edges) : {} as JsonObject;
          const rules = impact.rules ? object(impact.rules) : {} as JsonObject;
          const families = impact.deployment_families ? object(impact.deployment_families) : {} as JsonObject;
          return {
            answer: impact.answer as RequirementValue,
            added_component_ids: refs(components.added, 'component_id'),
            removed_component_ids: refs(components.removed, 'component_id'),
            added_edge_ids: (edges.added_edge_ids as string[]) ?? [],
            removed_edge_ids: (edges.removed_edge_ids as string[]) ?? [],
            activated_rule_ids: (rules.activated_rule_ids as string[]) ?? [],
            deactivated_rule_ids: (rules.deactivated_rule_ids as string[]) ?? [],
            feasible_pattern_ids: refs(families.feasible, 'pattern_id'),
            rejected_pattern_ids: refs(families.rejected, 'pattern_id'),
            unknown_pattern_ids: refs(families.unknown, 'pattern_id'),
          };
        }),
      };
    })() : null,
    decision_trace: (raw.decision_trace as JsonObject[]).map((entry) => ({
      evaluation_id: String(entry.evaluation_id),
      rule_id: String(entry.rule_id),
      effect: String(entry.effect) as 'require' | 'recommend' | 'exclude',
      requirement_ids: refs(entry.requirements, 'requirement_id'),
      target_component_ids: refs(entry.target_components, 'component_id'),
      target_pattern_ids: refs(entry.target_patterns, 'pattern_id'),
      evidence_claim_ids: entry.evidence_claim_ids as string[],
      rationale: String(entry.rationale),
    })),
    evidence: ((raw.evidence as JsonObject[]) ?? []).map((claim) => ({
      claim_id: String(claim.claim_id),
      statement: String(claim.statement),
      review_status: String(claim.review_status),
      effective_on: String(claim.effective_on),
      source_locator: String(claim.source_locator),
      source_id: String(claim.source_id),
      source_title: claim.source_title ? String(claim.source_title) : undefined,
      source_uri: claim.source_uri ? String(claim.source_uri) : undefined,
      source_publisher: claim.source_publisher ? String(claim.source_publisher) : undefined,
    })),
    decision_history: raw.decision_history as ArchitectureWorkspaceProjection['decision_history'],
  };
}

async function request(path: string, options: RequestInit = {}, retry = true): Promise<unknown> {
  const token = getAccessToken();
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 401 && retry && await refreshIdToken()) {
    return request(path, options, false);
  }
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text().catch(() => undefined);
    }
    throw new ArchitectureApiError(response.status, detail);
  }
  return response.json();
}

export async function getArchitectureWorkspace(
  scope?: ArchitectureWorkspaceScope,
): Promise<ArchitectureWorkspaceProjection> {
  return normalizeArchitectureProjection(await request(scopedPath('/architecture/workspace', scope)));
}

export interface ArchitectureEvaluationPayload {
  answers: Record<string, RequirementValue>;
  base_revision_number?: number;
  base_state_hash?: string;
}

export async function evaluateArchitectureWorkspace(
  payload: ArchitectureEvaluationPayload,
  scope?: ArchitectureWorkspaceScope,
): Promise<ArchitectureWorkspaceProjection> {
  return normalizeArchitectureProjection(await request(scopedPath('/architecture/workspace/evaluate', scope), {
    method: 'POST',
    body: JSON.stringify(payload),
  }));
}

export interface ExplainPassage {
  text: string;
  score: number;
  source: string;
}

export interface ArchitectureExplanation {
  query: string;
  configured: boolean;
  passages: ExplainPassage[];
}

export interface ChatResult {
  reply: string;
  proposed_answers: Record<string, RequirementValue>;
  source: string;
}

// Chat proposes a typed requirement patch. Only the workspace evaluate command
// can commit an accepted proposal.
export async function chatArchitecture(
  message: string,
  scope?: ArchitectureWorkspaceScope,
): Promise<ChatResult> {
  return await request(scopedPath('/architecture/chat', scope), {
    method: 'POST',
    body: JSON.stringify({ message }),
  }) as ChatResult;
}

// Reference-only retrieval. This never changes a decision — it surfaces
// supporting KB passages so a user can read more about a decision the
// deterministic engine already made.
export async function explainArchitectureDecision(
  query: string,
  topK = 4,
  scope?: ArchitectureWorkspaceScope,
): Promise<ArchitectureExplanation> {
  const raw = object(await request(scopedPath('/architecture/explain', scope), {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  }));
  return {
    query: String(raw.query ?? query),
    configured: Boolean(raw.configured),
    passages: ((raw.passages as JsonObject[]) ?? []).map((p) => ({
      text: String(p.text ?? ''),
      score: Number(p.score ?? 0),
      source: String(p.source ?? ''),
    })),
  };
}

export async function downloadArchitecturePackage(
  revisionNumber: number,
  scope?: ArchitectureWorkspaceScope,
): Promise<{ blob: Blob; filename: string; packageHash: string }> {
  const packageData = await request(scopedPath('/architecture/workspace/exports', scope), {
    method: 'POST',
    body: JSON.stringify({ revision_number: revisionNumber }),
  }) as JsonObject;
  const workspace = object(packageData.workspace);
  const revision = object(packageData.revision);
  const workspaceName = String(workspace.workspace_id ?? 'architecture')
    .replace(/[^a-zA-Z0-9_-]+/g, '-');
  const exportedRevision = Number(revision.revision_number ?? revisionNumber);
  return {
    blob: new Blob([`${JSON.stringify(packageData, null, 2)}\n`], {
      type: 'application/json',
    }),
    filename: `${workspaceName}-revision-${exportedRevision}.json`,
    packageHash: String(packageData.package_hash ?? ''),
  };
}
