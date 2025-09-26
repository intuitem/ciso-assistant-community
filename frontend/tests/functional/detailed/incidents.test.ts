import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { Page } from '@playwright/test';

async function redirectToIncidents(page: Page): Promise<void> {
	await page.getByTestId('accordion-item-operations').click();
	await page.getByTestId('accordion-item-incidents').click();
	await page.waitForTimeout(500);
}

test('Incidents full flow - creation, validation and cleanup', async ({
	page,
	logedPage,
	foldersPage
}) => {
	await test.step('Create folder and incident', async () => {
		await foldersPage.goto();
		await foldersPage.createItem({
			name: 'incidents-folder'
		});

		await redirectToIncidents(page);
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('incidents-test');

		page.getByTestId('form-input-severity').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-severity').selectOption('4');

		page.getByTestId('form-input-qualifications').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-qualifications').click();
		await page.getByRole('option', { name: 'authenticity' }).click();
		await page.getByRole('option', { name: 'availability' }).click();
		await page.getByRole('option', { name: 'confidentiality' }).click();
		await page.getByRole('option', { name: 'human' }).click();

		page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'incidents-folder' }).click();

		await page.getByTestId('form-input-ref-id').fill('test');
		await page.getByTestId('form-input-name').click();
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();

		await page
			.getByRole('gridcell', { name: 'New' })
			.getByTestId('model-table-td-array-elem')
			.waitFor({ state: 'visible' });
		await page
			.getByRole('gridcell', { name: 'Minor' })
			.getByTestId('model-table-td-array-elem')
			.waitFor({ state: 'visible' });
		await page
			.getByRole('gridcell', { name: 'Internal' })
			.getByTestId('model-table-td-array-elem')
			.waitFor({ state: 'visible' });
	});

	await test.step('Incidents detail view & second edit creating 1st incident', async () => {
		await page.getByText('incidents-test').click();
		await page.getByTestId('edit-button').click();

		page.getByTestId('form-input-detection').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-detection').selectOption({ label: 'External' });

		page.getByTestId('form-input-severity').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-severity').selectOption('2');

		page.getByTestId('form-input-status').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-status').selectOption({ label: 'Resolved' });

		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();
		await expect(page.getByText('Severity changed')).toBeVisible();
		await expect(page.getByText('Status changed')).toBeVisible();
		await expect(page.getByText('Minor->Major')).toBeVisible();
		await expect(page.getByText('New->Resolved')).toBeVisible();
	});

	await test.step('Incidents detail view & timeline incident detail view', async () => {
		await page.getByText('Minor->Major').click();
		await expect(page.locator('#page-title')).toHaveText('Minor->Major');

		await page.getByTestId('edit-button').click();
		// await page.getByTestId(`markdown-edit-btn-${field}`).click();
		await page
			.getByTestId('form-input-observation')
			.fill('This is an observation: I love mango juice but I prefer orange juice');
		await page.getByText('Save').click();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();

		await page.getByText('Add evidence').click();
		await page.getByTestId('form-input-name').fill('incidents-evidence-1');
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();

		await page
			.getByTestId('incident-field-value')
			.getByRole('link', { name: 'incidents-test' })
			.click();
		await expect(page.locator('#page-title')).toHaveText('incidents-test');
	});

	await test.step('Incidents detail view & Add an event', async () => {
		await page.getByTestId('form-input-entry').fill('entry 1');
		await page.getByTestId('save-button-event').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();
		await expect(page.getByTestId('name-entry-0')).toHaveText('entry 1');

		await page.getByTestId('form-input-entry').fill('entry 2');
		await page.getByTestId('form-input-entry-type').selectOption({ label: 'Mitigation' });
		await page.getByTestId('save-button-event').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();
		await expect(page.getByTestId('name-entry-0')).toHaveText('entry 2');

		await page.getByTestId('form-input-entry').fill('entry 3');

		await page.getByTestId('add-button-evidence').click();
		await page.getByTestId('form-input-name').fill('incidents-evidence-2');
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();
		await page.getByTestId('form-input-entry-type').selectOption({ label: 'Detection' });
		await page.getByTestId('save-button-event').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();
		await expect(page.getByTestId('name-entry-0')).toHaveText('entry 3');

		await expect(page.getByText('entry 1')).toBeVisible();
		await expect(page.getByText('entry 2')).toBeVisible();
		await expect(page.getByText('entry 3')).toBeVisible();
	});

	await test.step('Incidents detail view & verify timeline logic & timeline deletion', async () => {
		await expect(page.getByTestId('name-entry-0')).toHaveText('entry 3');
		await expect(page.getByTestId('name-entry-1')).toHaveText('entry 2');
		await expect(page.getByTestId('name-entry-2')).toHaveText('entry 1');
		await expect(page.getByTestId('name-entry-3')).toHaveText('Minor->Major');
		await expect(page.getByTestId('name-entry-4')).toHaveText('New->Resolved');

		await page.getByTestId('form-input-entry').fill('entry 4');
		await page.getByTestId('form-input-timestamp').fill('2024-07-17T16:19');

		await page.getByTestId('save-button-event').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.getByTestId('toast').getByLabel('Dismiss toast').click();
		await expect(page.getByTestId('toast')).not.toBeVisible();

		await expect(page.getByTestId('name-entry-5')).toHaveText('entry 4');

		await page.getByTestId('tablerow-delete-button').first().click();
		await page.getByTestId('delete-confirm-button').click();
		await page.reload();

		await expect(page.getByText('entry 4')).not.toBeVisible();
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

	const folderRow = page.getByRole('row', { name: /incidents-folder/i });

	await folderRow.getByTestId('tablerow-delete-button').click();

	await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();

	await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');

	await page.getByRole('button', { name: 'Submit' }).click();

	await expect(page.getByRole('row', { name: /incidents-folder/i })).toHaveCount(0);
});
