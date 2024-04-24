import { test } from '../utils/test-utils.js';

test('startup tests', async ({ loginPage, analyticsPage, page }) => {
	await test.step('proper redirection to the login page', async () => {
		await page.goto('/');
		await loginPage.hasUrl(1);
		await loginPage.login();
		await analyticsPage.hasUrl();
	});

	await test.step('proper redirection to the analytics page after login', async () => {
		await analyticsPage.hasUrl();
		await analyticsPage.hasTitle();
	});
});
