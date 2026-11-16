/**
 * The actor picker of a responsibility matrix has to find an actor from any
 * part of its name. A native select only jumps to entries starting with what
 * is typed, so analysts missed existing teams and created duplicates.
 */

import { test, expect } from '../../utils/test-utils.js';
import { m } from '#paraglide/messages.js';
import type { BrowserContext } from '@playwright/test';

const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

async function getAuthToken(context: BrowserContext): Promise<string> {
	const cookies = await context.cookies();
	const token = cookies.find((c) => c.name === 'token')?.value;
	if (!token) throw new Error('No `token` cookie found — is the user logged in?');
	return token;
}

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
	await create('teams', { name: network, folder: folderId });
	await create('teams', { name: security, folder: folderId });
	const matrix = await create('pmbok/responsibility-matrices', {
		name: `Actor search ${suffix}`,
		folder: folderId
	});

	await page.goto(`/responsibility-matrices/${matrix.id}`);
	await page.waitForLoadState('networkidle');
	await page.getByRole('button', { name: m.edit() }).click();

	const picker = page.getByTestId('form-input-actor');
	await picker.click();
	await picker.getByRole('combobox').fill(`operations ${suffix}`);

	await expect(page.getByRole('option', { name: network })).toBeVisible();
	await expect(page.getByRole('option', { name: security })).toHaveCount(0);

	await page.getByRole('option', { name: network }).click();
	await page.getByRole('button', { name: m.addActor() }).click();

	await expect(page.locator('main').getByText(network, { exact: true })).toBeVisible();
});
