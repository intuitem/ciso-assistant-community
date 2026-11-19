/**
 * The actor picker of a responsibility matrix has to find an actor from any
 * part of its name. A native select only jumps to entries starting with what
 * is typed, so analysts missed existing teams and created duplicates.
 */

import { test, expect } from '../../utils/test-utils.js';
import { BACKEND_API_URL, getAuthToken } from '../../utils/api.js';
import { m } from '#paraglide/messages.js';

test('the actor picker finds a team from the middle of its name', async ({
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
	const network = `Network operations ${suffix}`;
	const security = `Security ${suffix}`;
	// Team names are user data: one that happens to be a message key must not be translated.
	const keyLikeName = 'in_progress';
	await create('teams', { name: network, folder: folderId });
	await create('teams', { name: security, folder: folderId });
	await create('teams', { name: keyLikeName, folder: folderId });
	const matrix = await create('pmbok/responsibility-matrices', {
		name: `Actor search ${suffix}`,
		folder: folderId
	});

	await page.goto(`/responsibility-matrices/${matrix.id}`);
	await page.waitForLoadState('networkidle');
	await page.getByRole('button', { name: m.edit() }).click();

	const picker = page.getByRole('combobox', { name: m.addActor() });
	const addButton = page.getByRole('button', { name: m.addActor() });
	const addActor = async (search: string, name: string) => {
		await picker.fill(search);
		await page.getByRole('option', { name, exact: true }).click();
		await addButton.click();
		await expect(page.locator('main').getByText(name, { exact: true })).toBeVisible();
	};

	await picker.fill(`operations ${suffix}`);
	await expect(page.getByRole('option', { name: network })).toBeVisible();
	await expect(page.getByRole('option', { name: security })).toHaveCount(0);

	await addActor(`operations ${suffix}`, network);
	await expect(addButton).toBeDisabled();
	await picker.fill(`operations ${suffix}`);
	await expect(page.getByRole('option', { name: network })).toHaveCount(0);

	await addActor(security, security);

	// Reordering columns keeps their count: the picker must still list readable options.
	await page
		.locator('[draggable="true"]', { hasText: security })
		.dragTo(page.locator('[draggable="true"]', { hasText: network }));
	await picker.fill(keyLikeName);
	await expect(page.getByRole('option', { name: keyLikeName, exact: true }).first()).toBeVisible();
});
