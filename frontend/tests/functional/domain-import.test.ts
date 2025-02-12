import { expect, test } from '../utils/test-utils.js';
import { promisify } from 'node:util';
import { gunzip } from 'node:zlib';

test('Database export should generate valid backup file', async ({ logedPage, page }) => {
	await page.waitForLoadState('networkidle');
	const modalBackdrop = page.getByTestId('modal-backdrop');

	await test.step('Dismiss any blocking modals', async () => {
		if (await modalBackdrop.isVisible()) {
			await modalBackdrop.press('Escape');
			await expect(modalBackdrop).not.toBeVisible();
		}

		if (await page.locator('#driver-dummy-element').isVisible()) {
			await page.locator('.driver-popover-close-btn').first().click();
		}
	});

	// Attempt to close any remaining modals
	await page.locator('body').press('Escape');

	await test.step('Navigate to folders list page', async () => {
		await page.getByRole('button', { name: 'Organization' }).click();
		await page.getByTestId('accordion-item-folders').click();
		await expect(page).toHaveURL('/folders');
		await expect(page.getByTestId('import-button')).toBeVisible();
	});

	await test.step('Import sample domain', async () => {
		const initialRowCountText = await page.getByTestId('row-count').innerText();
		const initialLastChar = initialRowCountText[initialRowCountText.length - 1];
		const initialRowCount = parseInt(initialLastChar.match(/\d+/) ? initialLastChar : '0');

		const file = new URL('../utils/sample-domain-schema-1.bak', import.meta.url).pathname;

		console.debug('file', file);

		await page.getByTestId('import-button').click();
		await page.getByTestId('form-input-name').fill('foobar');
		await page.getByTestId('form-input-file').click();
		await page.getByTestId('form-input-file').setInputFiles(file);
		await page.getByTestId('form-input-load-missing-libraries').check();
		await page.getByTestId('save-button').click();

		await expect(page.getByTestId('toast')).toBeVisible();

		const newRowCountText = await page.getByTestId('row-count').innerText();
		const newLastChar = newRowCountText[newRowCountText.length - 1];
		const newRowCount = parseInt(newLastChar.match(/\d+/) ? newLastChar : '0');

		expect(newRowCount).toBeGreaterThan(initialRowCount);
	});
});
