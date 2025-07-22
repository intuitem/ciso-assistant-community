import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';

test('Analytics full flow - creation, validation and cleanup', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await test.step('Create folder and perimeter', async () => {
		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('analytics-folder');
		await page.getByTestId('save-button').click();

		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-perimeters').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('analytics-perimeter');
		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create Active control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-1');
		await page.getByTestId('form-input-status').selectOption('active');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create Deprecated control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-2');
		await page.getByTestId('form-input-status').selectOption('deprecated');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create to do control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-3');
		await page.getByTestId('form-input-status').selectOption('to_do');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create On hold control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-4');
		await page.getByTestId('form-input-status').selectOption('on_hold');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create In progress control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-5');
		await page.getByTestId('form-input-status').selectOption('in_progress');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create audit with NIST', async () => {
		await page.getByTestId('accordion-item-compliance').click();
		await page.getByTestId('accordion-item-compliance-assessments').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-audit-1');
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('form-input-framework').click();
		await page.getByRole('option', { name: 'NIST CSF' }).click();
		await page.getByTestId('form-input-perimeter').click();
		await page.getByRole('option', { name: 'analytics-folder/analytics-perimeter' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create audit with ISO 27001', async () => {
		await page.getByTestId('accordion-item-compliance').click();
		await page.getByTestId('accordion-item-compliance-assessments').click();
		await page.waitForTimeout(200);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-audit-2');
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('form-input-framework').click();
		await page.getByRole('option', { name: '27001' }).click();
		await page.getByTestId('form-input-perimeter').click();
		await page.getByRole('option', { name: 'analytics-folder/analytics-perimeter' }).click();
		await page.getByTestId('save-button').click();
	});
});

test('Cleanup - delete the folder', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByRole('button', { name: 'Organization' }).click();
	await page.getByTestId('accordion-item-folders').click();
	await page.waitForTimeout(200);

	const folderRow = page.getByRole('row', { name: /analytics-folder/i });
	await folderRow.getByTestId('tablerow-delete-button').click();
	await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
	await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
	await page.getByRole('button', { name: 'Submit' }).click();
	await expect(page.getByRole('row', { name: /analytics-folder/i })).toHaveCount(0);
});
