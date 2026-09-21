/**
 * The linked-object tabs of an applied control must let you attach an object
 * that is not in the list yet. The row checkboxes only drive bulk edits on
 * objects already linked, so without these buttons the relation is only
 * editable from the other side.
 *
 * Guards the `addExisting` mechanism itself: it renders through the create
 * button's slot, so a tab that disables creation silently drops it.
 */

import { test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import type { BrowserContext } from '@playwright/test';

const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

async function getAuthToken(context: BrowserContext): Promise<string> {
	const cookies = await context.cookies();
	const token = cookies.find((c) => c.name === 'token')?.value;
	if (!token) throw new Error('No `token` cookie found — is the user logged in?');
	return token;
}

test('an applied control tab can attach an object that is not linked yet', async ({
	logedPage,
	page,
	context
}) => {
	const token = await getAuthToken(context);
	const headers = { 'Content-Type': 'application/json', Authorization: `Token ${token}` };

	const folders = await page.request.get(`${BACKEND_API_URL}/folders/?content_type=GL`, {
		headers
	});
	const folderId = (await folders.json()).results[0].id;

	const create = async (model: string, data: Record<string, unknown>) => {
		const res = await page.request.post(`${BACKEND_API_URL}/${model}/`, { data, headers });
		expect(res.ok(), `POST ${model} failed: ${res.status()} ${await res.text()}`).toBeTruthy();
		return res.json();
	};

	const suffix = Date.now();
	const control = await create('applied-controls', {
		name: `Linked objects ${suffix}`,
		folder: folderId
	});
	const asset = await create('assets', { name: `Unlinked asset ${suffix}`, folder: folderId });

	await page.goto(`/applied-controls/${control.id}`);
	await page.waitForLoadState('networkidle');

	// Every tab the ticket covers must offer both actions, not just the one used below.
	for (const name of ['Documents', 'Findings', 'Assets', 'Incidents']) {
		const tab = page.getByRole('tab', { name: new RegExp(`^${name}`) });
		await tab.click();
		const panel = page.getByRole('tabpanel', { name: new RegExp(`^${name}`) });
		await expect(panel.getByTestId('select-existing-button')).toBeVisible();
		await expect(panel.getByTestId('add-button')).toBeVisible();
	}

	const assetsPanel = page.getByRole('tabpanel', { name: /^Assets/ });
	await page.getByRole('tab', { name: /^Assets/ }).click();
	await expect(assetsPanel.locator('table tbody tr')).toHaveCount(0);

	await assetsPanel.getByTestId('select-existing-button').click();
	await expect(page.getByTestId('modal-title')).toBeVisible();

	const field = page.getByTestId('form-input-assets');
	await field.click();
	await field.getByRole('combobox').fill(asset.name);
	await page
		.getByRole('option', { name: new RegExp(asset.name) })
		.first()
		.click();
	// The option list stays open over the modal footer when other options still
	// match, so it has to be dismissed before the buttons are clickable.
	await page.getByTestId('modal-title').click();

	// The select-existing modal has no testid on its footer buttons.
	const modal = page.locator('.modal-example-form');
	await modal.getByRole('button', { name: m.save() }).click();

	await expect(assetsPanel.getByText(asset.name)).toBeVisible();
});

/**
 * The modal PATCHes the whole relation, so it has to send the links that are
 * already there alongside the new one. It seeds itself from the parent's
 * update form, which drops any field the zod schema does not declare: a
 * missing declaration silently replaces the relation instead of extending it.
 *
 * Starting from an empty tab cannot catch that, which is why this one seeds a
 * link first.
 */
test('attaching a document keeps the ones already linked', async ({ logedPage, page, context }) => {
	const token = await getAuthToken(context);
	const headers = { 'Content-Type': 'application/json', Authorization: `Token ${token}` };

	const folders = await page.request.get(`${BACKEND_API_URL}/folders/?content_type=GL`, {
		headers
	});
	const folderId = (await folders.json()).results[0].id;

	const create = async (model: string, data: Record<string, unknown>) => {
		const res = await page.request.post(`${BACKEND_API_URL}/${model}/`, { data, headers });
		expect(res.ok(), `POST ${model} failed: ${res.status()} ${await res.text()}`).toBeTruthy();
		return res.json();
	};

	const suffix = Date.now();
	const control = await create('applied-controls', {
		name: `Keeps documents ${suffix}`,
		folder: folderId
	});
	const first = await create('document-containers', {
		name: `First document ${suffix}`,
		folder: folderId,
		document_type: 'policy'
	});
	const second = await create('document-containers', {
		name: `Second document ${suffix}`,
		folder: folderId,
		document_type: 'policy'
	});

	const seeded = await page.request.patch(`${BACKEND_API_URL}/applied-controls/${control.id}/`, {
		data: { control_documents: [first.id] },
		headers
	});
	expect(seeded.ok(), `seeding the first link failed: ${await seeded.text()}`).toBeTruthy();

	await page.goto(`/applied-controls/${control.id}`);
	await page.waitForLoadState('networkidle');

	const panel = page.getByRole('tabpanel', { name: /^Documents/ });
	await page.getByRole('tab', { name: /^Documents/ }).click();
	await expect(panel.getByText(first.name)).toBeVisible();

	await panel.getByTestId('select-existing-button').click();
	await expect(page.getByTestId('modal-title')).toBeVisible();

	const field = page.getByTestId('form-input-control-documents');
	await field.click();
	await field.getByRole('combobox').fill(second.name);
	await page
		.getByRole('option', { name: new RegExp(second.name) })
		.first()
		.click();
	await page.getByTestId('modal-title').click();

	await page.locator('.modal-example-form').getByRole('button', { name: m.save() }).click();

	await expect(panel.getByText(second.name)).toBeVisible();
	// The point of the test: the seeded link must not have been replaced.
	await expect(panel.getByText(first.name)).toBeVisible();
});
