import { PageContent } from '../../utils/page-content.js';
import { test, expect } from '../../utils/test-utils.js';

const JOURNEY_FOLDER_NAME_EN = 'Belgian Organisation - CyFun 2025';
const JOURNEY_FOLDER_REGEX = /Organisation belge.*CyFun 2025|Belgian Organisation.*CyFun 2025/i;
const PRESET_NAME = 'Test Preset E2E';

test.describe('Journeys', () => {
	test('journeys - belgian cyfun 2025', async ({ logedPage, page }) => {
		test.setTimeout(180_000);

		await test.step('navigate to presets page', async () => {
			await page.goto('/presets');
			await expect(page).toHaveURL(/.*presets.*/);
			await expect(page.getByTestId('available-templates-heading')).toBeVisible();
		});

		await test.step('find and click Start a journey on CyFun card', async () => {
			await expect(page.locator('[data-testid^="preset-card-"]').first()).toBeVisible({
				timeout: 30_000
			});

			const cyfunCard = page
				.locator('[data-testid^="preset-card-"]')
				.filter({
					has: page
						.locator('[data-testid^="preset-name-"]')
						.filter({ hasText: JOURNEY_FOLDER_REGEX })
				})
				.first();

			await expect(cyfunCard).toBeVisible({ timeout: 15_000 });

			const applyBtn = cyfunCard.locator('[data-testid^="preset-apply-"]');
			await applyBtn.scrollIntoViewIfNeeded();
			await expect(applyBtn).toBeVisible({ timeout: 5_000 });
			await page.waitForTimeout(2000);
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

			await page.waitForURL(/.*\/(journeys|preset-journeys)\/[a-z0-9-]+.*/, { timeout: 120_000 });
			await page.waitForLoadState('networkidle');
		});

		await test.step('verify journey dashboard loaded', async () => {
			await expect(page).toHaveURL(/.*\/(journeys|preset-journeys)\/.*/);
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(2_000);

			await expect(page.getByTestId('journey-header-name')).toBeVisible({ timeout: 30_000 });
			await expect(page.getByTestId('journey-header-name')).toContainText('CyFun 2025');
			await expect(page.getByTestId('journey-progress-title')).toBeVisible();
			await expect(page.getByTestId('journey-progress-percent')).toHaveText('0%');
		});

		await test.step('click hide descriptions and verify descriptions are hidden', async () => {
			const descriptionText =
				'Inventory primary assets (data, processes) and supporting assets (servers, applications, networks) within scope.';
			await expect(page.getByText(descriptionText)).toBeVisible();
			await page.getByTestId('journey-toggle-descriptions').click();
			await expect(page.getByText(descriptionText)).not.toBeVisible();
		});

		await test.step('click start on the first step (Identify your assets)', async () => {
			await page.getByTestId('journey-step-0-start').click();
			await expect(page).toHaveURL(/.*assets.*/);
		});

		await test.step('go back to journey page and verify step is in progress', async () => {
			await page.goBack();
			await expect(page).toHaveURL(/.*\/(journeys|preset-journeys)\/.*/);
			await expect(page.getByTestId('journey-step-0-status')).toHaveText(
				/in.progress|In progress/i
			);
			await expect(page.getByTestId('journey-step-0-mark-done')).toBeVisible();
			await expect(page.getByTestId('journey-step-0-skip')).toBeVisible();
		});

		await test.step('mark first step as done', async () => {
			await page.getByTestId('journey-step-0-mark-done').click();
			await page.waitForLoadState('networkidle');
		});

		await test.step('verify journey progress shows Done 1', async () => {
			await expect(page.getByTestId('journey-count-done')).toContainText('1');
			await expect(page.getByTestId('journey-progress-percent')).toHaveText(/12%|12\.5%/);
		});

		await test.step('delete the journey', async () => {
			await page.getByTestId('journey-delete-btn').click();
			await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
			await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
			await page.getByRole('button', { name: /submit/i }).click();
			await expect(page).toHaveURL(/.*presets.*/);
			await expect(page.getByTestId('available-templates-heading')).toBeVisible();
		});

		await test.step('cleanup - delete cyfun folder', async () => {
			await page.goto('/folders');
			await page.waitForLoadState('networkidle');
			const foldersPage = new PageContent(page, '/folders', 'Domains');
			const folderRow = foldersPage.getRow(JOURNEY_FOLDER_NAME_EN);
			const exists = await folderRow.isVisible({ timeout: 3_000 }).catch(() => false);
			if (exists) {
				await foldersPage.deleteItemButton(JOURNEY_FOLDER_NAME_EN).click();
				await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
				await foldersPage.deletePromptConfirmTextField().fill('yes');
				await foldersPage.deletePromptConfirmButton().click();
				await expect(foldersPage.getRow(JOURNEY_FOLDER_NAME_EN)).not.toBeVisible();
			}
		});
	});

	test('preset editor - create, publish and delete a blank preset', async ({ logedPage, page }) => {
		test.setTimeout(60_000);

		await test.step('navigate directly to preset editor', async () => {
			await page.goto('/experimental/preset-editor');
			await page.waitForLoadState('networkidle');
			await expect(page.getByRole('heading', { name: /preset editor/i })).toBeVisible({
				timeout: 10_000
			});
		});

		await test.step('click Create blank preset', async () => {
			await page.getByRole('button', { name: /create blank preset/i }).click();
			await page.waitForLoadState('networkidle');
			await expect(page).toHaveURL(/.*preset-editor\/.+/);
		});

		await test.step('fill in the preset name', async () => {
			const nameInput = page.locator('input[placeholder="Preset name"]');
			await expect(nameInput).toBeVisible();
			await nameInput.fill(PRESET_NAME);
			await page.waitForTimeout(300);
		});

		await test.step('save the draft', async () => {
			const saveBtn = page.locator('button[title="Save draft"]');
			await expect(saveBtn).toBeEnabled({ timeout: 5_000 });
			await saveBtn.click();
			await page.waitForTimeout(500);
		});

		await test.step('publish the preset', async () => {
			const publishBtn = page.locator('button[title="Publish the draft"]');
			await expect(publishBtn).toBeVisible();
			await publishBtn.click();
			await page.waitForLoadState('networkidle');
		});

		await test.step('navigate to /presets and verify preset is listed', async () => {
			await page.goto('/presets');
			await page.waitForLoadState('networkidle');
			await expect(
				page.locator('[data-testid^="preset-name-"]').filter({ hasText: PRESET_NAME }).first()
			).toBeVisible({ timeout: 10_000 });
		});

		await test.step('go back to preset editor and delete all test presets', async () => {
			// Reload to ensure busy state is reset after publish
			await page.goto('/experimental/preset-editor');
			await page.waitForLoadState('networkidle');

			// Delete all presets named PRESET_NAME (cleanup any leftover from failed runs)
			let deleteCount = 0;
			while (deleteCount < 10) {
				const row = page.locator('tr').filter({ hasText: PRESET_NAME }).first();
				const exists = await row.isVisible({ timeout: 2_000 }).catch(() => false);
				if (!exists) break;

				const deleteBtn = row.getByRole('button', { name: /delete/i });
				// Wait up to 10s for button to become enabled (busy state clears after fetch)
				await expect(deleteBtn).toBeEnabled({ timeout: 10_000 });
				page.once('dialog', (dialog) => dialog.accept());
				await deleteBtn.click();
				// Reload after each delete to get fresh state
				await page.goto('/experimental/preset-editor');
				await page.waitForLoadState('networkidle');
				deleteCount++;
			}
			console.log(`Deleted ${deleteCount} preset(s) named "${PRESET_NAME}"`);
		});

		await test.step('verify all test presets are removed', async () => {
			await expect(page.getByRole('link', { name: PRESET_NAME })).not.toBeVisible({
				timeout: 5_000
			});
		});
	});
});
