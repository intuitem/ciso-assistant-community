import { test, expect } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';

test('My assignments full flow - creation, validation, negative case and cleanup', async ({
	page
}) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();

	await test.step('Create folder and perimeter', async () => {
		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('my-assignments-folder');
		await page.getByTestId('save-button').click();

		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-perimeters').click();
		await page.waitForTimeout(500);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('my-assignments-perimeter');
		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'my-assignments-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create risk assessment', async () => {
		await page.getByTestId('accordion-item-risk').click();
		await page.getByTestId('accordion-item-risk-assessments').click();
		await page.waitForTimeout(500);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-risk-assessment');
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('form-input-perimeter').click();
		await page
			.getByRole('option', { name: 'my-assignments-folder/my-assignments-perimeter' })
			.click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create control with owner', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(500);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-control');
		await page.getByTestId('form-input-owner').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'my-assignments-folder' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create audit', async () => {
		await page.getByTestId('accordion-item-compliance').click();
		await page.getByTestId('accordion-item-compliance-assessments').click();
		await page.waitForTimeout(500);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('test-audit');
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('form-input-framework').click();
		await page.getByRole('option', { name: 'NIST CSF' }).click();
		await page.getByTestId('form-input-perimeter').click();
		await page
			.getByRole('option', { name: 'my-assignments-folder/my-assignments-perimeter' })
			.click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Verify my assignments contains created entities', async () => {
		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-my-assignments').click();
		await page.waitForTimeout(500);

		await expect(page.getByText('test-control')).toBeVisible();
		await expect(page.getByText('test-risk-assessment')).toBeVisible();
		await expect(page.getByText('test-audit')).toBeVisible();
	});

	await test.step('Create control without owner and verify absence in my assignments', async () => {
		await page.getByText('Operations').click();
		await page.getByTestId('accordion-item-applied-controls').click();
		await page.waitForTimeout(500);

		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').fill('control-without-owner');
		await page.getByTestId('form-input-folder').waitFor({ state: 'visible' });
		await page.getByTestId('form-input-folder').click();
		await page.getByRole('option', { name: 'my-assignments-folder' }).click();
		await page.getByTestId('save-button').click();

		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-my-assignments').click();
		await page.waitForTimeout(500);

		await expect(page.getByText('control-without-owner')).toHaveCount(0);
	});

	await test.step('Cleanup - delete the folder', async () => {
		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await page.waitForTimeout(500);

		const folderRow = page.getByRole('row', { name: /my-assignments-folder/i });
		await folderRow.getByTestId('tablerow-delete-button').click();
		await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
		await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
		await page.getByRole('button', { name: 'Submit' }).click();
		await expect(page.getByRole('row', { name: /my-assignments-folder/i })).toHaveCount(0);
	});
});
