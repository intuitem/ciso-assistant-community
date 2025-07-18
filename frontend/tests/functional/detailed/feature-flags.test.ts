import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';

test('Feature Flags - X-Rays and Inherent Risk visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByText('Extra').click();
	await page.getByText('Settings').click();
	await expect(page).toHaveURL('/settings');

	await page.getByText(/^ Feature flags$/).click();

	const xraysToggle = page.getByTestId('form-input-xrays');
	const inherentRiskToggle = page.getByTestId('form-input-inherent-risk');

	try {
		if (await xraysToggle.isChecked()) {
			await xraysToggle.click();
		}
		if (await inherentRiskToggle.isChecked()) {
			await inherentRiskToggle.click();
		}

		await page.getByRole('button', { name: 'Save' }).click();
		await page.waitForTimeout(500);

		await page.reload();
		await page.waitForTimeout(500);

		await page.getByText('Operations').click();
		await expect(page.getByText('X-Rays', { exact: false })).not.toBeVisible();

		const risksPage = new PageContent(page, '/risk-scenarios', 'Risk Scenarios');
		await risksPage.goto();
		await expect(page.getByText('Inherent Level', { exact: false })).not.toBeVisible();
	} finally {
		await page.goto('/settings');
		await page.getByText(/^ Feature flags$/).click();

		if (!(await xraysToggle.isChecked())) {
			await xraysToggle.click();
		}
		if (!(await inherentRiskToggle.isChecked())) {
			await inherentRiskToggle.click();
		}

		await page.getByRole('button', { name: 'Save' }).click();
		await page.waitForTimeout(500);
	}
});
