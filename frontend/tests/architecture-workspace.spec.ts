import { expect, test, type Locator, type Page } from 'playwright/test';
import {
  authenticate,
  mockArchitectureApi,
  workspaceUrl,
} from './support/architecture-api';

test.beforeEach(async ({ context, baseURL }) => {
  await authenticate(context, baseURL);
});

async function openWorkspace(page: Page): Promise<void> {
  await page.goto(workspaceUrl);
  await expect(page.getByRole('heading', { name: 'Acme Coding Platform' })).toBeVisible();
  await expect(page.locator('.react-flow')).toBeVisible();
}

test('first use loads a useful baseline and preserves customer scope', async ({ page }) => {
  const api = await mockArchitectureApi(page);
  await openWorkspace(page);

  await expect(page.getByLabel('Architecture workflow')).toContainText(
    'BaselineEngine projection loaded',
  );
  await expect(page.getByRole('tab', { name: 'Questions' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('Guided discovery')).toBeVisible();
  await expect(page.getByText('8 decisions remaining')).toBeVisible();
  await expect(page.getByRole('heading', {
    name: 'What minimum isolation boundary must separate coding-agent execution?',
  })).toBeVisible();
  await expect(page.getByText('Publication status')).toHaveCount(0);
  await expect(page.getByLabel('Customer discovery message')).toHaveCount(0);

  const load = api.requests.find((request) =>
    request.method === 'GET' && request.pathname.endsWith('/architecture/workspace'));
  expect(load?.search).toBe('?customer_id=cust-acme&session_id=sess-blueprint');
});

test('chat proposal rejection never commits an architecture mutation', async ({ page }) => {
  const api = await mockArchitectureApi(page);
  await openWorkspace(page);
  await page.getByRole('tab', { name: 'Ask advisor' }).click();

  await page.getByLabel('Customer discovery message')
    .fill('Use microVM isolation for every coding task');
  await page.getByRole('button', { name: 'Send discovery message' }).click();

  const proposal = page.locator('.fw-proposal');
  await expect(proposal.getByText('Review proposed answers')).toBeVisible();
  await expect(proposal.getByText('Runtime isolation')).toBeVisible();
  await page.getByRole('button', { name: 'Reject', exact: true }).click();

  await expect(page.getByText('Proposal rejected. The architecture was not changed.')).toBeVisible();
  expect(api.requests.filter((request) =>
    request.pathname.endsWith('/architecture/workspace/evaluate'))).toHaveLength(0);
});

test('chat proposal acceptance sends the typed patch and optimistic revision tokens', async ({ page }) => {
  const api = await mockArchitectureApi(page);
  await openWorkspace(page);
  await page.getByRole('tab', { name: 'Ask advisor' }).click();

  await page.getByLabel('Customer discovery message')
    .fill('Use microVM isolation for every coding task');
  await page.keyboard.press('Enter');
  await expect(page.locator('.fw-proposal').getByText('Review proposed answers')).toBeVisible();
  await page.getByRole('button', { name: 'Accept', exact: true }).click();

  await expect(page.getByText(/Accepted 1 change/)).toBeVisible();
  await page.getByRole('button', { name: 'Review package' }).click();
  await expect(page.getByText(/Revision 3 \| catalog/)).toBeVisible();

  const evaluate = api.requests.find((request) =>
    request.pathname.endsWith('/architecture/workspace/evaluate'));
  expect(evaluate?.search).toBe('?customer_id=cust-acme&session_id=sess-blueprint');
  expect(evaluate?.body).toMatchObject({
    base_revision_number: 2,
    base_state_hash: 'sha256:persistence-2',
    answers: {
      'requirement:runtime-isolation': 'microvm',
    },
  });
});

test('package review exposes deployable alternatives and customer delivery lenses', async ({ page }) => {
  await mockArchitectureApi(page);
  await openWorkspace(page);

  await page.getByRole('button', { name: 'Review package' }).click();
  await expect(page.getByText('Customer architecture package')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recommended deployable solution' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Alternatives and decision matrix' })).toBeVisible();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('#1 AWS governed managed stack', { exact: true })).toBeVisible();
  await expect(dialog.getByText('#2 Hybrid governed stack', { exact: true })).toBeVisible();
  await expect(dialog.getByText('#3 BYOP portable stack', { exact: true })).toBeVisible();
  await expect(dialog.getByText('#4 Open-source sovereign stack', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Assurance, economics, and outcomes' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Implementation roadmap' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision and evidence trace' })).toBeVisible();
});

test('offline baseline is explicit and cannot be mistaken for a successful live load', async ({ page }) => {
  await mockArchitectureApi(page, { getStatus: 503 });
  await openWorkspace(page);

  await expect(page.locator('[role="alert"]').filter({ hasText: 'Read-only snapshot' })).toContainText(
    'Read-only snapshot. The live engine is unreachable',
  );
  await expect(page.getByText('Guided discovery')).toBeVisible();
  await page.getByRole('tab', { name: 'Ask advisor' }).click();
  await expect(page.getByLabel('Customer discovery message')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Review package' })).toBeVisible();
});

test('stale write does not silently dismiss or commit the pending proposal', async ({ page }) => {
  const api = await mockArchitectureApi(page, { evaluateStatus: 409 });
  await openWorkspace(page);
  await page.getByRole('tab', { name: 'Ask advisor' }).click();

  await page.getByLabel('Customer discovery message')
    .fill('Use microVM isolation for every coding task');
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Accept', exact: true }).click();

  await expect(page.getByText(
    'The proposal was not committed. Reload the workspace before retrying.',
  )).toBeVisible();
  await expect(page.locator('.fw-proposal').getByText('Review proposed answers')).toBeVisible();
  await expect(page.locator('[role="alert"]').filter({ hasText: 'revision is stale' })).toContainText(
    'This revision is stale. Reload before making or publishing changes.',
  );
  expect(api.requests.filter((request) =>
    request.pathname.endsWith('/architecture/workspace/evaluate'))).toHaveLength(1);
});

test('guided discovery presents one decision and applies an explicit answer', async ({ page }) => {
  const api = await mockArchitectureApi(page);
  await openWorkspace(page);

  const microVm = page.getByRole('radio', { name: /MicroVM/i });
  await microVm.click();
  await expect(microVm).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('button', { name: 'Apply answer' })).toBeVisible();
  await page.getByRole('button', { name: 'Apply answer' }).click();

  const evaluate = api.requests.find((request) =>
    request.pathname.endsWith('/architecture/workspace/evaluate'));
  expect(evaluate?.body).toMatchObject({
    answers: {
      'requirement:runtime-isolation': 'microvm',
    },
  });
});

async function boxesDoNotOverlap(first: Locator, second: Locator): Promise<void> {
  const [a, b] = await Promise.all([first.boundingBox(), second.boundingBox()]);
  expect(a).not.toBeNull();
  expect(b).not.toBeNull();
  const overlaps = a!.x < b!.x + b!.width
    && a!.x + a!.width > b!.x
    && a!.y < b!.y + b!.height
    && a!.y + a!.height > b!.y;
  expect(overlaps).toBe(false);
}

test('desktop and mobile layouts keep primary workspace regions separated', async ({ page }) => {
  await mockArchitectureApi(page);
  await openWorkspace(page);

  await boxesDoNotOverlap(page.locator('.fw-head'), page.locator('.fw-journey'));
  await boxesDoNotOverlap(page.locator('.fw-journey'), page.locator('.fw-main'));
  await boxesDoNotOverlap(page.locator('.fw-canvas-wrap'), page.locator('.fw-aside'));

  const horizontalOverflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(horizontalOverflow).toBeLessThanOrEqual(1);
});
