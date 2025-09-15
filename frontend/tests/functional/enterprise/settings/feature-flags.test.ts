/**
 * Enterprise feature flags tests
 */

import { test, expect, type Page } from '../../../utils/test-utils.js';
import { PageContent } from '../../../utils/page-content.js';
import { TestContent } from '../../../utils/test-utils.js';

const vars = TestContent.generateTestVars();

const toggleFeatureFlag = async (page: Page, flagTestId: string, enable: boolean) => {
	await page.getByTestId('accordion-item-extra').click();
	await page.getByTestId('accordion-item-settings').click();
	await expect(page).toHaveURL('/settings');
	await page.getByText(/^ Feature flags$/).click();

	const toggle = page.getByTestId(`form-input-${flagTestId}`);
	if ((await toggle.isChecked()) !== enable) {
		await toggle.click();
		await page.getByRole('button', { name: 'Save' }).click();
		await page.reload();
		await expect(page).toHaveURL('/settings');
		await page.reload();
		await expect(page.getByText(/^ Feature flags$/)).toBeVisible();
	}
};

// ---------- Publish ----------
test('Feature Flags - Publish', async ({ logedPage, foldersPage, assetsPage, page }) => {
	await test.step('Create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.hasUrl();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
	});

	await test.step('Create asset', async () => {
		await assetsPage.goto();
		await assetsPage.hasUrl();
		await assetsPage.createItem({
			name: vars.assetName,
			description: vars.description,
			folder: vars.folderName,
			type: 'Primary'
		});
	});

	await test.step("Check that 'publish' button is not visible", async () => {
		await assetsPage.viewItemDetail(vars.assetName);
		await expect(page.getByTestId('unpublish-button')).not.toBeVisible();
	});

	await test.step("Enable 'publish' feature flag", async () => {
		await toggleFeatureFlag(page, 'publish', true);
	});

	await test.step("Check that 'publish' button is visible and can be used", async () => {
		await assetsPage.goto();
		await assetsPage.hasUrl();
		await assetsPage.viewItemDetail(vars.assetName);

		await expect(page.getByTestId('unpublish-button')).toBeVisible();

		await test.step('unpublish', async () => {
			await page.getByTestId('unpublish-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			await page.getByTestId('form-unpublish-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
		});

		await test.step('publish', async () => {
			await expect(page.getByTestId('publish-button')).toBeVisible();
			await page.getByTestId('publish-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			await page.getByTestId('form-publish-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
		});

		await expect(page.getByTestId('unpublish-button')).toBeVisible();
	});

	await toggleFeatureFlag(page, 'publish', false);
});
