import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';

const toggleFeatureFlag = async (page, flagTestId, enable) => {
	await page.getByTestId('accordion-item-extra').click();
	await page.getByTestId('accordion-item-settings').click();
	await expect(page).toHaveURL('/settings');
	await page.getByText(/^ Feature flags$/).click();

	const toggle = page.getByTestId(`form-input-${flagTestId}`);
	if ((await toggle.isChecked()) !== enable) {
		await toggle.click();
		await page.getByRole('button', { name: 'Save' }).click();
		await page.waitForTimeout(500);
		await page.reload();
	}
};

// ---------- X-Rays ----------
test('Feature Flags - X-Rays visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByText('Operations').click();
	await expect(page.getByText('X-Rays', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'xrays', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('X-Rays', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'xrays', true);
});

// ---------- Incidents ----------
test('Feature Flags - Incidents visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByText('Operations').click();
	await expect(page.getByText('Incidents', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'incidents', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('Incidents', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'incidents', true);
});

// ---------- Tasks ----------
test('Feature Flags - Tasks visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByText('Operations').click();
	await expect(page.getByText('Tasks', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'tasks', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('Tasks', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'tasks', true);
});

// ---------- Risk Acceptances ----------
test('Feature Flags - Risk Acceptances visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Risk Acceptances', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'risk-acceptances', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Risk Acceptances', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'risk-acceptances', true);
});

// ---------- Exceptions ----------
test('Feature Flags - Exceptions visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Exceptions', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'exceptions', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Exceptions', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'exceptions', true);
});

// ---------- Findings Tracking ----------
test('Feature Flags - Findings Tracking visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Findings Tracking', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'follow-up', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Findings Tracking', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'follow-up', true);
});

// ---------- Ebios RM ----------
test('Feature Flags - Ebios RM visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByTestId('accordion-item-ebios-rm')).toBeVisible();

	await toggleFeatureFlag(page, 'ebiosrm', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByTestId('accordion-item-ebios-rm')).not.toBeVisible();

	await toggleFeatureFlag(page, 'ebiosrm', true);
});

// ---------- Scoring Assistant ----------
test('Feature Flags - Scoring Assistant visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Scoring Assistant', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'scoring-assistant', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Scoring Assistant', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'scoring-assistant', true);
});

// ---------- Vulnerabilities ----------
test('Feature Flags - Vulnerabilities visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Vulnerabilities', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'vulnerabilities', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Vulnerabilities', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'vulnerabilities', true);
});

// ---------- Compliance ----------
test('Feature Flags - Compliance visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await expect(page.getByTestId('accordion-item-compliance')).toBeVisible();

	await toggleFeatureFlag(page, 'compliance', false);

	await expect(page.getByTestId('accordion-item-compliance')).not.toBeVisible();

	await toggleFeatureFlag(page, 'compliance', true);
});

// ---------- Third Party ----------
test('Feature Flags - Third Party visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await expect(page.getByTestId('accordion-item-thirdpartycategory')).toBeVisible();

	await toggleFeatureFlag(page, 'tprm', false);

	await expect(page.getByTestId('accordion-item-thirdpartycategory')).not.toBeVisible();

	await toggleFeatureFlag(page, 'tprm', true);
});

// ---------- Privacy ----------
test('Feature Flags - Privacy visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await expect(page.getByText('Privacy', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'privacy', false);

	await expect(page.getByText('Privacy', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'privacy', true);
});

// ---------- Experimental ----------
test('Feature Flags - Experimental visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByText('Extra').click();
	await expect(page.getByText('Experimental', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'experimental', false);

	await page.getByText('Extra').click();
	await expect(page.getByText('Experimental', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'experimental', true);
});

// ---------- Inherent Risk ----------
test('Feature Flags - Inherent Risk visibility toggling', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	const risksPage = new PageContent(page, '/risk-scenarios', 'Risk Scenarios');
	await risksPage.goto();
	await expect(page.getByText('Inherent Level', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', false);

	await risksPage.goto();
	await expect(page.getByText('Inherent Level', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});
