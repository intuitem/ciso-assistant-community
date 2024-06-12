import { test } from '../utils/test-utils.js';

test('startup tests', async ({ loginPage, birdEyePage, page }) => {
	await test.step('proper redirection to the login page', async () => {
		await page.goto('/');
		await loginPage.hasUrl(1);
		await loginPage.login();
		await birdEyePage.hasUrl();
	});

	await test.step('proper redirection to the analytics page after login', async () => {
		await birdEyePage.hasUrl();
		await birdEyePage.hasTitle();
	});
});
