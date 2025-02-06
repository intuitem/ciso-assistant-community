import { expect, setHttpResponsesListener, test } from '../utils/test-utils.js';

test('Database export should generate valid backup file', async ({ logedPage, page }) => {
	await page.waitForTimeout(1000);

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

	await test.step('Navigate to backup/restore section', async () => {
		await page.getByRole('button', { name: 'Extra' }).click();
		await page.getByTestId('accordion-item-backup-restore').click();
		await expect(page).toHaveURL('/backup-restore');
		await expect(page.getByRole('button', { name: 'Export database' })).toBeVisible();
	});

	await test.step('Initiate and verify database export', async () => {
		const downloadPromise = page.waitForEvent('download');
		await page.getByRole('button', { name: 'Export database' }).click();

		const download = await downloadPromise;
		const fileName = download.suggestedFilename();

		// Verify filename pattern
		await test.step('Verify download metadata', async () => {
			expect(fileName.endsWith('.bak')).toBeTruthy();
		});

		await test.step('Verify file contents', async () => {
			const stream = await download.createReadStream();
			const content: string = await new Promise((resolve) => {
				let data = '';
				stream?.on('data', (chunk) => (data += chunk));
				stream?.on('end', () => resolve(data));
			});
			expect(content.length).toBeGreaterThan(0);
		});

		await test.step('Save downloaded file', async () => {
			await download.saveAs(`./${fileName}`);
		});

		await test.step('Check that export file can be imported back', async () => {
			await page.locator('#file').click();
			await page.locator('#file').setInputFiles(fileName);
			await page.getByRole('button', { name: 'Upload' }).click();
			await page.getByTestId('delete-prompt-confirm-textfield').click();
			await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
			await page.getByRole('button', { name: 'Submit' }).click();

			await page.waitForTimeout(1000);

			// Sessions are not preserved after importing the backup
			await expect(page).toHaveURL('/login');
		});
	});
});
