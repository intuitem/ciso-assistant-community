import { expect, test as setup } from '@playwright/test';

const STATE = 'tests/docs-screenshots/.auth/state.json';

setup('authenticate', async ({ page }) => {
	const email = process.env.DOCS_SHOTS_EMAIL ?? 'admin@demo.local';
	const password = process.env.DOCS_SHOTS_PASSWORD ?? 'Demo1234!';

	await page.goto('/login');
	await page.locator('body[data-hydrated="true"]').waitFor();
	await page.getByTestId('form-input-username').fill(email);
	await page.getByTestId('form-input-password').fill(password);
	await page.getByTestId('login-btn').click();

	await expect(page).not.toHaveURL(/\/login/);
	await page.context().storageState({ path: STATE });
});
