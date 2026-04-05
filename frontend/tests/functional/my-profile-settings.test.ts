import { expect, test } from '../utils/test-utils.js';

test('my profile settings page loads correctly', async ({ logedPage, page }) => {
	await test.step('navigate to my profile settings page', async () => {
		await page.goto('/my-profile/settings');
		await expect(page).toHaveURL('/my-profile/settings');
	});

	await test.step('security settings section is visible', async () => {
		await expect(page.locator('h3').filter({ hasText: 'Security settings' })).toBeVisible();
	});

	await test.step('multi-factor authentication section is visible', async () => {
		await expect(
			page.locator('dt').filter({ hasText: 'Multi-factor authentication' })
		).toBeVisible();
		await expect(page.locator('h6').filter({ hasText: 'Authenticator app' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Enable MFA' })).toBeVisible();
	});

	await test.step('security keys section is visible', async () => {
		await expect(page.locator('dt').filter({ hasText: 'Security keys' })).toBeVisible();
		await expect(page.locator('h6').filter({ hasText: 'Security keys' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Add security key' })).toBeVisible();
	});

	await test.step('personal access tokens section is visible', async () => {
		await expect(page.locator('dt').filter({ hasText: 'Personal Access Tokens' })).toBeVisible();
	});
});
