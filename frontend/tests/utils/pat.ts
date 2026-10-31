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
	const res = await page.request.get(`${BACKEND_API_URL}/iam/current-user/`, {
		headers: { Authorization: `Token ${token}` }
	});
	expect(res.status()).toBe(200);
	return token;
}
