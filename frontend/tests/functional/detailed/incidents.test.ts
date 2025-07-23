import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { Page } from '@playwright/test';

async function redirectToIncidents(page: Page): Promise<void> {
	await page.getByTestId('accordion-item-operations').click();
	await page.getByTestId('accordion-item-incidents').click();
	await page.waitForTimeout(500);
}

test('Incidents full flow - creation, validation and cleanup', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await test.step('Create folder and incident', async () => {
		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('incidents-folder');
		await page.getByTestId('save-button').click();

		await redirectToIncidents(page);
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('incidents-test');

		page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'incidents-folder' }).click();

		page.getByTestId('form-input-severity').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-severity').click();
		await page.getByRole('option', { name: 'minor' }).click();

		page.getByTestId('form-input-qualifications').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-qualifications').click();
		await page.getByRole('option', { name: 'authenticity' }).click();
		await page.getByRole('option', { name: 'availability' }).click();
		await page.getByRole('option', { name: 'confidentiality' }).click();
		await page.getByRole('option', { name: 'human' }).click();

		await page.getByTestId('save-button').click();

		await page.getByText('New').waitFor({ state: 'visible' });
		await page.getByText('Minor').waitFor({ state: 'visible' });
		await page.getByText('Internal').waitFor({ state: 'visible' });
	});

	await test.step('Incidents detail view & second edit creating 1st incident', async () => {
		await page.getByText('incidents-test').click();
		await page.getByTestId('edit-button').click();

		page.getByTestId('form-input-detection').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-detection').click();
		await page.getByRole('option', { name: 'external' }).click();

		page.getByTestId('form-input-severity').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-severity').click();
		await page.getByRole('option', { name: 'major' }).click();

		page.getByTestId('form-input-status').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-status').click();
		await page.getByRole('option', { name: 'resolved' }).click();

		await page.getByTestId('save-button').click();
		await expect(page.getByText('Severity changed')).toBeVisible();
		await expect(page.getByText('Status changed')).toBeVisible();
		await expect(page.getByText('Unknown->Major')).toBeVisible();
		await expect(page.getByText('New->Resolved')).toBeVisible();
	});

	await test.step('Incidents detail view & timeline incident detail view', async () => {
		await page.getByText('Unknown->Major').click();
		await page.getByTestId('edit-button').click();
		await page
			.getByTestId('form-input-observation')
			.fill('This is an observation: I love ciso assistant');
		await page.getByTestId('save-button').click();

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('incidents-evidence-1');
		await page.getByTestId('save-button').click();
	});
});
