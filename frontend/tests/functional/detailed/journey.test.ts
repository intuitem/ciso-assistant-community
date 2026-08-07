import { PageContent } from '../../utils/page-content.js';
import { test, expect } from '../../utils/test-utils.js';

const PRESET_NAME_PREFIX = 'Test Preset E2E';

test.describe('Journeys', () => {
	test('author a preset library, apply it as journey, complete a step, then cleanup', async ({
		logedPage,
		page
	}, testInfo) => {
		const runId = `${testInfo.workerIndex}-${testInfo.retry}-${Date.now()}`;
		const PRESET_NAME = `${PRESET_NAME_PREFIX} ${runId}`;
		const FOLDER_NAME = PRESET_NAME;
		// Library identity must be URN-safe ([a-z0-9_-]).
		const LIBRARY_REF_ID = `e2e-journey-${runId}`;
		test.setTimeout(180_000);

		let libraryEditorUrl = '';

		await test.step('create a library draft', async () => {
			await page.goto('/experimental/library-builder');
			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /new library draft/i }).click();
			await page.locator('input[placeholder="My security library"]').fill(PRESET_NAME);
			await page.locator('input[placeholder="my-org"]').fill('e2e-tests');
			await page.locator('input[placeholder="my-library"]').fill(LIBRARY_REF_ID);
			const createBtn = page.getByRole('button', { name: /^create$/i });
			await expect(createBtn).toBeEnabled();
			await createBtn.click();
			await page.waitForURL(/.*library-builder\/[a-f0-9-]+$/, { timeout: 15_000 });
			await page.waitForLoadState('networkidle');
			libraryEditorUrl = page.url();
		});

		await test.step('open the journey preset editor', async () => {
			await page.getByRole('link', { name: /create journey/i }).click();
			await page.waitForURL(/.*library-builder\/[a-f0-9-]+\/preset$/, { timeout: 15_000 });
			await page.waitForLoadState('networkidle');
		});

		await test.step('fill preset name', async () => {
			const nameInput = page.locator('input[placeholder="Preset name"]');
			await expect(nameInput).toBeVisible({ timeout: 10_000 });
			await nameInput.fill(PRESET_NAME);
			await page.waitForTimeout(300);
		});

		await test.step('add a step', async () => {
			await page.getByRole('button', { name: /add step/i }).click();
			await page.waitForTimeout(300);
		});

		await test.step('save to the library draft', async () => {
			const saveBtn = page.locator('button[title="Save to the library draft"]');
			await expect(saveBtn).toBeEnabled({ timeout: 5_000 });
			await saveBtn.click();
			await page.waitForTimeout(500);
		});

		await test.step('publish the library', async () => {
			await page.goto(libraryEditorUrl);
			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /^publish$/i }).click();
			// Publishing loads the library; the header badge flips to Published.
			await expect(page.getByText('Published', { exact: true })).toBeVisible({
				timeout: 30_000
			});
		});

		await test.step('navigate to /presets and verify preset is listed', async () => {
			await page.goto('/presets');
			await page.waitForLoadState('networkidle');
			await expect
				.poll(
					async () => {
						await page.reload({ waitUntil: 'networkidle' });
						return await page
							.locator('[data-testid^="preset-name-"]')
							.filter({ hasText: PRESET_NAME })
							.count();
					},
					{ timeout: 60_000, intervals: [1_000, 2_000, 5_000] }
				)
				.toBeGreaterThan(0);
		});

		await test.step('click Start a journey on the new preset card', async () => {
			const presetCard = page
				.locator('[data-testid^="preset-card-"]')
				.filter({
					has: page.locator('[data-testid^="preset-name-"]').filter({ hasText: PRESET_NAME })
				})
				.first();

			await expect(presetCard).toBeVisible({ timeout: 15_000 });

			const applyBtn = presetCard.locator('[data-testid^="preset-apply-"]');
			await applyBtn.scrollIntoViewIfNeeded();
			await expect(applyBtn).toBeVisible({ timeout: 5_000 });
			await page.waitForTimeout(1500);
			await applyBtn.dispatchEvent('click');
			await page.waitForTimeout(500);
		});

		await test.step('confirm journey creation in modal', async () => {
			const confirmBtn = page.getByTestId('apply-preset-confirm-btn');
			const submitBtn = page.locator('button[type="submit"]').first();

			await Promise.race([
				confirmBtn.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => null),
				submitBtn.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => null)
			]);

			const confirmVisible = await confirmBtn.isVisible().catch(() => false);
			if (confirmVisible) {
				await confirmBtn.click();
			} else {
				await submitBtn.click();
			}

			await page.waitForURL(/.*\/(journeys|preset-journeys)\/[a-z0-9-]+.*/, {
				timeout: 120_000
			});
			await page.waitForLoadState('networkidle');
		});

		await test.step('verify journey dashboard loaded', async () => {
			await expect(page).toHaveURL(/.*\/(journeys|preset-journeys)\/.*/);
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(2_000);

			await expect(page.getByTestId('journey-header-name')).toBeVisible({ timeout: 30_000 });
			await expect(page.getByTestId('journey-header-name')).toContainText(PRESET_NAME_PREFIX);
			await expect(page.getByTestId('journey-progress-title')).toBeVisible();
			await expect(page.getByTestId('journey-progress-percent')).toHaveText('0%');
		});

		await test.step('start the first step', async () => {
			await page.getByTestId('journey-step-0-start').click();
			await page.waitForTimeout(500);
		});

		await test.step('mark first step as done', async () => {
			await page.getByTestId('journey-step-0-mark-done').click();
			await page.waitForLoadState('networkidle');
		});

		await test.step('verify progress shows Done 1 and 100%', async () => {
			await expect(page.getByTestId('journey-count-done')).toContainText('1');
			await expect(page.getByTestId('journey-progress-percent')).toHaveText('100%');
		});

		await test.step('delete the journey', async () => {
			await page.getByTestId('journey-delete-btn').click();
			await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
			await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
			await page.getByRole('button', { name: /submit/i }).click();
			await expect(page).toHaveURL(/.*presets.*/);
			await expect(page.getByTestId('available-templates-heading')).toBeVisible();
		});

		await test.step('cleanup - delete folder created by preset', async () => {
			await page.goto('/folders');
			await page.waitForLoadState('networkidle');
			const foldersPage = new PageContent(page, '/folders', 'Domains');
			const folderRow = foldersPage.getRow(FOLDER_NAME);
			const exists = await folderRow.isVisible({ timeout: 3_000 }).catch(() => false);
			if (exists) {
				await foldersPage.deleteItemButton(FOLDER_NAME).click();
				await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
				await foldersPage.deletePromptConfirmTextField().fill('yes');
				await foldersPage.deletePromptConfirmButton().click();
				await expect(foldersPage.getRow(FOLDER_NAME)).not.toBeVisible();
			}
		});

		await test.step('cleanup - delete the library draft', async () => {
			await page.goto('/experimental/library-builder');
			await page.waitForLoadState('networkidle');

			const row = page.locator('tr').filter({ hasText: PRESET_NAME }).first();
			const exists = await row.isVisible({ timeout: 3_000 }).catch(() => false);
			if (exists) {
				page.once('dialog', (dialog) => dialog.accept());
				await row.getByRole('button', { name: /delete draft/i }).click();
				await expect(page.locator('tr').filter({ hasText: PRESET_NAME })).not.toBeVisible({
					timeout: 5_000
				});
			}
		});
	});
});
