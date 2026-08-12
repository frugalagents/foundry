import { expect, test } from 'playwright/test';
import {
  authenticate,
  mockArchitectureApi,
  publishableProjection,
  workspaceUrl,
} from './support/architecture-api';

test.beforeEach(async ({ context, baseURL }) => {
  await authenticate(context, baseURL);
});

test('logical and deployable views are explicit, keyboard operable, and preserve one revision', async ({ page }) => {
  await mockArchitectureApi(page);
  await page.goto(workspaceUrl);

  const logical = page.getByRole('button', { name: 'Logical', exact: true });
  const deployable = page.getByRole('button', { name: 'Deployable', exact: true });
  await expect(logical).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Provisional reviewed guidance')).toBeVisible();
  await expect(page.getByText('BYOP portable platform')).toBeVisible();
  await expect(page.getByText(/Potential fit, but customer decisions/i)).toBeVisible();
  await expect(page.getByText('10 capabilities | 12 relationships')).toBeVisible();
  await expect(page.getByRole('button', { name: /Coding agent runtime:/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Code context & task memory:/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Source control:/i })).toBeVisible();
  await deployable.focus();
  await page.keyboard.press('Enter');
  await expect(deployable).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Provisional pattern: BYOP portable stack').first()).toBeVisible();

  await page.getByRole('button', { name: /Review draft/ }).click();
  await expect(page.getByRole('dialog')).toContainText('Revision 2 | catalog 3.0.0');
});

test('offline mode disables mutations and immutable package export', async ({ page }) => {
  await mockArchitectureApi(page, { getStatus: 503 });
  await page.goto(workspaceUrl);

  await expect(page.locator('[role="alert"]').filter({ hasText: 'Read-only snapshot' }))
    .toContainText(/Read-only snapshot/);
  await page.getByRole('tab', { name: 'Ask advisor' }).click();
  await expect(page.getByLabel('Customer discovery message')).toBeDisabled();
  await page.getByRole('button', { name: /Review draft/ }).click();
  await expect(page.getByRole('button', { name: 'Download immutable package' })).toBeDisabled();
});

test('stale writes show a conflict state and offer latest-revision recovery', async ({ page }) => {
  await mockArchitectureApi(page, { evaluateStatus: 409 });
  await page.goto(workspaceUrl);
  await page.getByRole('tab', { name: 'Ask advisor' }).click();

  await page.getByLabel('Customer discovery message').fill('Use microVM isolation');
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Accept', exact: true }).click();

  await expect(page.locator('[role="alert"]').filter({ hasText: 'revision is stale' }))
    .toContainText(/revision is stale/i);
  await expect(page.getByRole('button', { name: 'Reload', exact: true })).toBeVisible();
  await expect(page.getByLabel('Customer discovery message')).toBeDisabled();
});

test('canvas decisions and package dialog are fully keyboard accessible', async ({ page }) => {
  await mockArchitectureApi(page);
  await page.goto(workspaceUrl);

  const node = page.getByRole('button', { name: /Coding agent runtime:/i });
  await node.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.fw-inspector-head h2')).toHaveText('Coding agent runtime');
  await expect(page.getByText(/Multi-agent workflows require orchestration and supervision/i))
    .toBeVisible();

  await page.getByRole('button', { name: /Review draft/ }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(page.getByRole('button', { name: 'Close package review' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: /Review draft/ })).toBeFocused();
});

test('publishable package downloads with pinned revision and state hash', async ({ page }) => {
  const api = await mockArchitectureApi(page, {
    initialProjection: publishableProjection(),
  });
  await page.goto(workspaceUrl);
  await page.getByRole('button', { name: 'Review package' }).click();

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download immutable package' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('workspace-acme-revision-7.json');

  const exportRequest = api.requests.find((request) =>
    request.pathname.endsWith('/architecture/workspace/exports'));
  expect(exportRequest?.search).toBe('?customer_id=cust-acme&session_id=sess-blueprint');
  expect(exportRequest?.body).toEqual({
    revision_number: 7,
  });
});
