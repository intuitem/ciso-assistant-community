import { test, expect } from '../../../utils/test-utils.js';

test.describe.configure({ mode: 'serial' });

test.describe('SSO settings', () => {
	test.beforeEach(async ({ logedPage, settingsPage, page }) => {
		await settingsPage.goto();
		await settingsPage.hasUrl();
		await settingsPage.hasTitle();
	});

	test('SAML settings', async ({ logedPage, page }) => {
		await test.step('configure SAML', async () => {
			await page.getByRole('tab', { name: ' SSO' }).click();
			await page.getByTestId('form-input-is-enabled').check();
			await page.getByTestId('form-input-idp-entity-id').click();
			await page.getByTestId('form-input-idp-entity-id').fill('http://localhost:8080/realms/test');
			await page.getByTestId('form-input-sp-entity-id').click();
			await page.getByTestId('form-input-sp-entity-id').fill('ciso-assistant-saml');
			await page.getByTestId('form-input-metadata-url').click();
			await page
				.getByTestId('form-input-metadata-url')
				.fill('http://localhost:8080/realms/test/protocol/saml/descriptor');
			await page.getByRole('button', { name: 'Save' }).click();
			const toast = page.getByTestId('toast');
			await expect(toast).toBeVisible();
		});
		await test.step('user should be able to login using SAML', async () => {
			await page.getByTestId('sidebar-more-btn').click();
			await page.getByTestId('logout-button').click();
			await expect(page).toHaveURL('/login');
			await expect(page.getByRole('button', { name: 'Login with SSO' })).toBeVisible();
			await page.getByRole('button', { name: 'Login with SSO' }).click();
			await expect(page).toHaveURL(/http:\/\/localhost:8080\/realms\/test\/protocol\/saml.*/);
			await page.getByRole('textbox', { name: 'Username or email' }).click();
			await page.getByRole('textbox', { name: 'Username or email' }).fill('admin@tests.com');
			await page.waitForTimeout(300);
			await page.getByRole('textbox', { name: 'Password' }).click();
			await page.getByRole('textbox', { name: 'Password' }).fill('1234');
			await page.waitForTimeout(300);
			await page.getByRole('button', { name: 'Sign In' }).click();
			await expect(page).toHaveURL('/analytics');
		});
	});

	test('OIDC settings', async ({ logedPage, page }) => {
		await test.step('configure OIDC', async () => {
			await page.getByRole('tab', { name: ' SSO' }).click();
			await page.getByTestId('form-input-is-enabled').check();
			await page.getByTestId('form-input-idp-entity-id').clear();
			// await page.getByTestId('form-input-sp-entity-id').clear();
			await page.getByTestId('form-input-metadata-url').clear();
			await page.getByText('OpenID Connect').click();
			await page.getByTestId('form-input-client-id').click();
			await page.getByTestId('form-input-client-id').fill('ciso-assistant-oidc');
			await page.getByTestId('form-input-secret').click();
			await page.getByTestId('form-input-secret').fill('foobar');
			await page.getByTestId('form-input-server-url').click();
			await page
				.getByTestId('form-input-server-url')
				.fill('http://localhost:8080/realms/test/.well-known/openid-configuration');
			await page.getByRole('button', { name: 'Save' }).click();
			const toast = page.getByTestId('toast');
			await expect(toast).toBeVisible();
		});
		await test.step('user should be able to login using OIDC', async () => {
			await page.getByTestId('sidebar-more-btn').click();
			await page.getByTestId('logout-button').click();
			await expect(page).toHaveURL('/login');
			await expect(page.getByRole('button', { name: 'Login with SSO' })).toBeVisible();
			await page.getByRole('button', { name: 'Login with SSO' }).click();
			await expect(page).toHaveURL(
				/http:\/\/localhost:8080\/realms\/test\/protocol\/openid-connect.*/
			);
			await page.getByRole('textbox', { name: 'Username or email' }).click();
			await page.getByRole('textbox', { name: 'Username or email' }).fill('admin@tests.com');
			await page.waitForTimeout(300);
			await page.getByRole('textbox', { name: 'Password' }).click();
			await page.getByRole('textbox', { name: 'Password' }).fill('1234');
			await page.waitForTimeout(300);
			await page.getByRole('button', { name: 'Sign In' }).click();
			await expect(page).toHaveURL('/analytics');
		});
	});
});
