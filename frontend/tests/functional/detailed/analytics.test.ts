import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { Page } from '@playwright/test';

async function redirectToAnalytics(page: Page): Promise<void> {
	await page.getByTestId('accordion-item-overview').click();
	await page.getByTestId('accordion-item-analytics').click();
	await expect(page.locator('#page-title')).toHaveText('Analytics');
	await expect(page).toHaveURL('/analytics');
}

test('Analytics full flow - creation, validation and cleanup', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await test.step('Create folder and perimeter', async () => {
		await page.getByText('Load demo data').click();
		await expect(page.locator('#page-title')).toHaveText('Analytics');

		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('analytics-folder');
		await page.getByTestId('save-button').click();

		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-perimeters').click();
		await expect(page.locator('#page-title')).toHaveText('Perimeters');
		await expect(page).toHaveURL('/perimeters');

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
		await expect(page.locator('#page-title')).toHaveText('Applied controls');
		await expect(page).toHaveURL('/applied-controls');

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
		await expect(page.locator('#page-title')).toHaveText('Applied controls');
		await expect(page).toHaveURL('/applied-controls');

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control-2');
		await page.getByTestId('form-input-status').selectOption('deprecated');

		await page.getByTestId('form-input-eta').fill('2023-11-11');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create to do control', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await expect(page.locator('#page-title')).toHaveText('Applied controls');
		await expect(page).toHaveURL('/applied-controls');

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
		await expect(page.locator('#page-title')).toHaveText('Applied controls');
		await expect(page).toHaveURL('/applied-controls');

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
		await expect(page.locator('#page-title')).toHaveText('Applied controls');
		await expect(page).toHaveURL('/applied-controls');

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
		await expect(page.locator('#page-title')).toHaveText('Audits');
		await expect(page).toHaveURL('/compliance-assessments');

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
		await expect(page.locator('#page-title')).toHaveText('Audits');
		await expect(page).toHaveURL('/compliance-assessments');

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

	await test.step('Create evidence', async () => {
		await page.getByTestId('accordion-item-compliance').click();
		await page.getByTestId('accordion-item-evidences').click();
		await expect(page.locator('#page-title')).toHaveText('Evidences');
		await expect(page).toHaveURL('/evidences');

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-evidence');

		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'analytics-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create risk assessment', async () => {
		await page.getByTestId('accordion-item-risk').click();
		await page.getByTestId('accordion-item-risk-assessments').click();
		await expect(page.locator('#page-title')).toHaveText('Risk assessments');
		await expect(page).toHaveURL('/risk-assessments');

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-risk-assessment');

		await page.getByTestId('form-input-perimeter').click();
		await page.getByRole('option', { name: 'analytics-folder/analytics-perimeter' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Verify data view in analytics', async () => {
		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-analytics').click();
		await expect(page.locator('#page-title')).toHaveText('Analytics');
		await expect(page).toHaveURL('/analytics');

		await expect(page.getByTestId('card-controls-total')).toHaveText('46');
		await expect(page.getByTestId('card-controls-active')).toHaveText('4');
		await expect(page.getByTestId('card-controls-deprecated')).toHaveText('2');
		await expect(page.getByTestId('card-controls-to do')).toHaveText('2');
		await expect(page.getByTestId('card-controls-in progress')).toHaveText('5');
		await expect(page.getByTestId('card-controls-on hold')).toHaveText('1');
		await expect(page.getByTestId('card-controls-Missed ETA')).toHaveText('6');

		await expect(page.getByText('test-audit-1')).toBeVisible();
		await expect(page.getByText('test-audit-2')).toBeVisible();

		await expect(page.getByTestId('card-compliance-Used frameworks')).toHaveText('3');
		await expect(page.getByTestId('card-compliance-Evidences')).toHaveText('6');
		await expect(page.getByTestId('card-risk-Assessments')).toHaveText('2');

		let analyticsPage = new PageContent(page, '/analytics?tab=governance', 'Analytics');
		await analyticsPage.goto();
		await expect(page.getByTestId('card-Applied controls')).toHaveText('46');
		await expect(page.getByTestId('card-Risk assessments')).toHaveText('2');
		await expect(page.getByTestId('card-Audits')).toHaveText('5');
		await expect(page.getByText('NIST CSF v2.0')).toBeVisible();
		await expect(page.getByText('International standard ISO/IEC 27001:2022')).toBeVisible();
		await expect(page.getByText('test-control-2')).toBeVisible();
	});

	await test.step('Verify redirection in analytics', async () => {
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-total').click();
		await expect(page).toHaveURL('/applied-controls');
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-active').click();
		await expect(page).toHaveURL('/applied-controls?status=active');
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-deprecated').click();
		await expect(page).toHaveURL('/applied-controls?status=deprecated');
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-to do').click();
		await expect(page).toHaveURL('/applied-controls?status=to_do');
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-in progress').click();
		await expect(page).toHaveURL('/applied-controls?status=in_progress');
		await redirectToAnalytics(page);

		await page.getByTestId('card-controls-on hold').click();
		await expect(page).toHaveURL('/applied-controls?status=on_hold');
		await redirectToAnalytics(page);

		await page.getByTestId('card-compliance-Used frameworks').click();
		await expect(page).toHaveURL('/frameworks');
		await redirectToAnalytics(page);

		await page.getByTestId('card-compliance-Evidences').click();
		await expect(page).toHaveURL('/evidences');
		await redirectToAnalytics(page);

		await page.getByTestId('card-risk-Assessments').click();
		await expect(page).toHaveURL('/risk-assessments');
		await redirectToAnalytics(page);
	});
});

test('Cleanup - delete the folder', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await page.getByRole('button', { name: 'Organization' }).click();
	await page.getByTestId('accordion-item-folders').click();
	await expect(page.locator('#page-title')).toHaveText('Domains');
	await expect(page).toHaveURL('/folders');

	let folderRow = page.getByRole('row', { name: /analytics-folder/i });
	await folderRow.getByTestId('tablerow-delete-button').click();
	await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
	await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
	await page.getByRole('button', { name: 'Submit' }).click();
	await expect(page.getByRole('row', { name: /analytics-folder/i })).toHaveCount(0);

	folderRow = page.getByRole('row', { name: /DEMO/i });
	await folderRow.getByTestId('tablerow-delete-button').click();
	await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
	await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
	await page.getByRole('button', { name: 'Submit' }).click();
	await expect(page.getByRole('row', { name: /DEMO/i })).toHaveCount(0);
});
