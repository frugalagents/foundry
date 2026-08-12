import type { BrowserContext, Page, Route } from 'playwright/test';
import baselineProjection from '../../data/architecture-workspace.json';

export type ProjectionDocument = typeof baselineProjection & {
  workspace: typeof baselineProjection.workspace & {
    persistence_revision?: number;
    persistence_hash?: string;
  };
  decision_guidance?: {
    candidate_id: string;
    template_id: string;
    pattern_id: string;
    title: string;
    summary: string;
    decision: string;
    fit: {
      status: 'compatible' | 'conditional' | 'incompatible';
      summary: string;
      matched_requirements: unknown[];
      conditional_requirements: unknown[];
    };
    recommended_when: string[];
    avoid_when: string[];
    tradeoffs: string[];
    reviewed_at: string;
    reviewer_ids: string[];
    evidence: {
      claim_id: string;
      statement: string;
      review_status: string;
      effective_from: string;
      stale_after: string;
      source_snapshot_id: string;
      source_id: string;
      source_name: string;
      source_publisher: string;
      source_uri: string;
      source_locator: string;
      authority_tier: string;
    }[];
    advisory: true;
  }[];
};

export interface RecordedArchitectureRequest {
  method: string;
  pathname: string;
  search: string;
  body?: Record<string, unknown>;
}

export interface ArchitectureApiOptions {
  initialProjection?: ProjectionDocument;
  getStatus?: number;
  evaluateStatus?: number;
  chatStatus?: number;
  chatResponse?: {
    reply: string;
    proposed_answers: Record<string, string | number | boolean | null>;
    source: string;
  };
  evaluate?: (
    body: Record<string, unknown>,
    current: ProjectionDocument,
  ) => ProjectionDocument;
}

export interface ArchitectureApiMock {
  requests: RecordedArchitectureRequest[];
  projection: ProjectionDocument;
}

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export function projectionAtRevision(
  revisionNumber: number,
  answers: Record<string, string | number | boolean | null> = {},
): ProjectionDocument {
  const projection = clone(baselineProjection) as ProjectionDocument;
  projection.workspace.persistence_revision = revisionNumber;
  projection.workspace.persistence_hash = `sha256:persistence-${revisionNumber}`;
  projection.revision.revision_number = revisionNumber;
  projection.revision.revision_id = `revision:r-${revisionNumber}`;
  projection.revision.state_hash = `sha256:state-${revisionNumber}`;
  projection.decision_guidance = [{
    candidate_id: 'bundle:byop-portable-r2',
    template_id: 'bundle-template:byop-portable',
    pattern_id: 'decision-pattern:byop-portable',
    title: 'BYOP portable platform',
    summary: 'Preserve replaceable provider boundaries through governed contracts.',
    decision: 'Use explicit platform contracts and adapters around customer-selected services.',
    fit: {
      status: 'conditional',
      summary: 'Potential fit, but customer decisions or implementation conditions remain unresolved.',
      matched_requirements: [],
      conditional_requirements: [],
    },
    recommended_when: [
      'Long-running or durable remote workspaces are required.',
      'Provider portability is a strategic requirement.',
    ],
    avoid_when: [
      'Fastest initial delivery is the dominant objective.',
    ],
    tradeoffs: [
      'Portability increases integration and conformance work.',
    ],
    reviewed_at: '2026-08-11T12:00:00+00:00',
    reviewer_ids: ['person:principal-platform-architect'],
    evidence: [{
      claim_id: 'claim:architecture-first-authority',
      statement: 'Provider-neutral architecture and deterministic constraints precede named service selection.',
      review_status: 'approved',
      effective_from: '2026-07-30',
      stale_after: '2036-07-27',
      source_snapshot_id: 'source:platform-advisor-vision',
      source_id: 'source:platform-advisor-vision',
      source_name: 'Platform Advisor product vision',
      source_publisher: 'Platform Advisor',
      source_uri: 'https://example.invalid/platform-advisor-vision',
      source_locator: 'Vision and Product Principles',
      authority_tier: 'tier_a_decision_authority',
    }],
    advisory: true,
  }];

  for (const requirement of projection.requirements) {
    if (!(requirement.requirement_id in answers)) continue;
    requirement.value = answers[requirement.requirement_id] as never;
    requirement.status = answers[requirement.requirement_id] == null ? 'unknown' : 'answered';
    requirement.source = 'user';
    requirement.assumption = null;
  }
  return projection;
}

export function publishableProjection(): ProjectionDocument {
  const projection = projectionAtRevision(7);
  for (const requirement of projection.requirements) {
    requirement.status = 'answered';
    requirement.source = 'user';
    requirement.assumption = null;
    if (requirement.value == null) requirement.value = true as never;
  }
  projection.deployment_families[0].status = 'feasible';
  projection.deployment_families[0].rejection_rule_ids = [];
  projection.deployment_families[0].blocking_requirements = [];

  const evidence = {
    claim_id: 'claim:playwright-approved',
    statement: 'Test evidence approved for deterministic package export.',
    review_status: 'approved',
    effective_on: '2026-07-31',
    source_locator: 'tests/architecture-workspace.contract.spec.ts',
    source_id: 'source:playwright',
    source_title: 'Playwright acceptance fixture',
    source_uri: 'https://example.invalid/playwright',
    source_publisher: 'Platform Advisor tests',
  };
  const mutable = projection as unknown as {
    evidence: typeof evidence[];
    decision_trace: { evidence_claim_ids: string[] }[];
    assurance: {
      security: {
        controls: { status: string; evidence_ids: string[] }[];
        high_or_critical_residual_count: number;
      };
      economics: { unit_costs: { status: string }[] };
    };
  };
  mutable.evidence = [evidence];
  for (const trace of mutable.decision_trace) {
    trace.evidence_claim_ids = [evidence.claim_id];
  }
  for (const control of mutable.assurance.security.controls) {
    control.status = 'verified';
    control.evidence_ids = [evidence.claim_id];
  }
  mutable.assurance.security.high_or_critical_residual_count = 0;
  for (const cost of mutable.assurance.economics.unit_costs) {
    cost.status = 'evidence_backed';
  }
  return projection;
}

export async function authenticate(
  context: BrowserContext,
  baseURL = 'http://127.0.0.1:3100',
): Promise<void> {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    sub: 'playwright-user',
    email: 'architect@example.com',
    'cognito:groups': ['user'],
    'custom:role': 'user',
    'custom:display_name': 'Test Architect',
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url');
  const token = `${header}.${payload}.test`;

  await context.addCookies([
    { name: 'id_token', value: token, url: baseURL },
    { name: 'access_token', value: token, url: baseURL },
  ]);
}

async function fulfillJson(route: Route, status: number, body: unknown): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

export async function mockArchitectureApi(
  page: Page,
  options: ArchitectureApiOptions = {},
): Promise<ArchitectureApiMock> {
  const requests: RecordedArchitectureRequest[] = [];
  let projection = options.initialProjection
    ? clone(options.initialProjection)
    : projectionAtRevision(2);

  await page.route('**/api/v1/architecture/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const body = request.postData()
      ? request.postDataJSON() as Record<string, unknown>
      : undefined;
    requests.push({
      method: request.method(),
      pathname: url.pathname,
      search: url.search,
      body,
    });

    if (url.pathname.endsWith('/architecture/workspace') && request.method() === 'GET') {
      const status = options.getStatus ?? 200;
      await fulfillJson(route, status, status === 200 ? projection : { detail: 'engine unavailable' });
      return;
    }

    if (url.pathname.endsWith('/architecture/workspace/evaluate')) {
      const status = options.evaluateStatus ?? 200;
      if (status !== 200) {
        await fulfillJson(route, status, {
          detail: status === 409 ? 'stale workspace revision' : 'evaluation failed',
        });
        return;
      }
      projection = options.evaluate
        ? options.evaluate(body ?? {}, projection)
        : projectionAtRevision(3, (body?.answers ?? {}) as Record<string, string | number | boolean | null>);
      await fulfillJson(route, 200, projection);
      return;
    }

    if (url.pathname.endsWith('/architecture/chat')) {
      const status = options.chatStatus ?? 200;
      await fulfillJson(route, status, status === 200
        ? options.chatResponse ?? {
          reply: 'I mapped the stated isolation boundary to a typed requirement.',
          proposed_answers: { 'requirement:runtime-isolation': 'microvm' },
          source: 'deterministic-test-double',
        }
        : { detail: 'chat unavailable' });
      return;
    }

    if (url.pathname.endsWith('/architecture/workspace/exports')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'Content-Disposition': 'attachment; filename="acme-architecture-package.json"',
          'Access-Control-Expose-Headers': 'Content-Disposition',
        },
        body: JSON.stringify({
          schema_version: '1.0.0',
          package_type: 'platform-advisor.customer-architecture',
          workspace: {
            workspace_id: 'workspace:acme',
            scope: {
              type: 'customer_session',
              customer_id: 'cust-acme',
              session_id: 'sess-blueprint',
            },
          },
          revision: {
            revision_number: projection.revision.revision_number,
            state_hash: projection.workspace.persistence_hash,
          },
          package_hash: 'sha256:playwright-package',
        }),
      });
      return;
    }

    await fulfillJson(route, 404, { detail: 'unexpected architecture route' });
  });

  return {
    requests,
    get projection() {
      return projection;
    },
  };
}

export const workspaceUrl =
  '/architecture?type=agentic-coding&bp=Acme%20Coding%20Platform&desc=Secure%20enterprise%20delivery&customer=cust-acme&session=sess-blueprint';
