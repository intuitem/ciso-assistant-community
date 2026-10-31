import { expect, type Page } from '@playwright/test';

const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

/** Reauthenticates with `password`, generates a PAT and checks the API accepts it. */
export async function generateWorkingPat(page: Page, password: string, name: string) {
	await page.goto('/my-profile/settings');
	await expect(page).toHaveURL(/\/reauthenticate\?method=password&next=/);
	await page.getByTestId('form-input-password').fill(password);
	await page.getByTestId('reauthenticate-button').click();
	// A sensitive action must not log the user out (regressed for SSO sessions, #4895).
	await expect(page).toHaveURL('/my-profile/settings');

	await page.getByRole('button', { name: 'Generate new token' }).click();
	const modal = page.getByTestId('modal-component');
	await modal.getByTestId('form-input-name').fill(name);
	await modal.getByRole('button', { name: 'Generate new token' }).click();
	await expect(
		modal.getByText('The token will only be displayed once', { exact: false })
	).toBeVisible();

	const token = await modal.locator('input[readonly]').inputValue();
	expect(token).not.toBe('');
	const headers = { Authorization: `Token ${token}` };
	const res = await page.request.get(`${BACKEND_API_URL}/iam/current-user/`, { headers });
	expect(res.status()).toBe(200);

	// Revoke it: users are capped at 5 active PATs, shared across tests and browser projects.
	const tokens = await (
		await page.request.get(`${BACKEND_API_URL}/iam/auth-tokens/`, { headers })
	).json();
	const digest = tokens.find((t: { name: string }) => t.name === name)?.digest;
	expect(digest).toBeTruthy();
	const del = await page.request.delete(`${BACKEND_API_URL}/iam/auth-tokens/${digest}/`, {
		headers
	});
	expect(del.status()).toBe(204);
}
