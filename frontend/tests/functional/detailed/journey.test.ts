import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { test, expect } from '../../utils/test-utils.js';

const JOURNEY_FOLDER_NAME = 'Belgian Organisation - CyFun 2025';

test.describe('Journeys', () => {
	test('journeys - belgian cyfun 2025', async ({ logedPage, page }) => {
		test.setTimeout(180_000);

		await test.step('navigate to journeys page', async () => {
			await page.goto('/presets');
			await expect(page).toHaveURL(/.*presets.*/);
			await expect(page.getByTestId('available-templates-heading')).toBeVisible();
		});

		await test.step('filter by BE', async () => {
			await page.getByTestId('filter-be').click();
			await expect(
				page
					.locator('[data-testid^="preset-name-"]')
					.filter({ hasText: JOURNEY_FOLDER_NAME })
					.first()
			).toBeVisible();
		});

		await test.step('start a journey for Belgian Organisation - CyFun 2025', async () => {
			const cyfunCard = page
				.locator('[data-testid^="preset-card-"]')
				.filter({
					has: page
						.locator('[data-testid^="preset-name-"]')
						.filter({ hasText: JOURNEY_FOLDER_NAME })
				})
				.first();

			const applyBtn = cyfunCard.getByTestId(/^preset-apply-/);
			await expect(applyBtn).toBeVisible({ timeout: 10_000 });
			await applyBtn.click();
			await page.waitForLoadState('networkidle');
		});

		await test.step('confirm journey creation in modal', async () => {
			const modal = page.getByTestId('modal-component');
			const modalVisible = await modal.isVisible({ timeout: 5_000 }).catch(() => false);

			if (modalVisible) {
				const submitBtn = modal.locator('button[type=submit]');
				await expect(submitBtn).toBeVisible();
				await submitBtn.click();
			}

			await page.waitForURL(/.*preset-journeys\/[a-z0-9-]+.*/, { timeout: 120_000 });
			await page.waitForLoadState('networkidle');
		});

		await test.step('verify journey dashboard loaded', async () => {
			await expect(page).toHaveURL(/.*preset-journeys.*/);

			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(2_000);

			const testIds = await page
				.locator('[data-testid]')
				.evaluateAll((els) => els.map((el) => el.getAttribute('data-testid')));
			console.log('data-testid found on page:', JSON.stringify(testIds));

			const h2Text = await page
				.locator('h2')
				.first()
				.textContent()
				.catch(() => 'none');
			console.log('First h2 text:', h2Text);

			await expect(page.getByTestId('journey-header-name')).toHaveText(
				'Belgian Organisation - CyFun 2025',
				{ timeout: 30_000 }
			);
			await expect(page.getByTestId('journey-progress-title')).toBeVisible();
			await expect(page.getByTestId('journey-progress-percent')).toHaveText('0%');
		});

		await test.step('click hide descriptions and verify descriptions are hidden', async () => {
			await expect(
				page.getByText(
					'Inventory primary assets (data, processes) and supporting assets (servers, applications, networks) within scope.'
				)
			).toBeVisible();
			await page.getByTestId('journey-toggle-descriptions').click();
			await expect(
				page.getByText(
					'Inventory primary assets (data, processes) and supporting assets (servers, applications, networks) within scope.'
				)
			).not.toBeVisible();
		});

		await test.step('click start on the first step (Identify your assets)', async () => {
			await page.getByTestId('journey-step-0-start').click();
			await expect(page).toHaveURL(/.*assets.*/);
		});

		await test.step('go back to journey page and verify step is in progress', async () => {
			await page.goBack();
			await expect(page).toHaveURL(/.*preset-journeys.*/);
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
			await expect(page.getByText('Available Templates')).toBeVisible();
		});
	});

	test.afterAll('cleanup - delete cyfun folder', async ({ browser }) => {
		const page = await browser.newPage();
		const loginPage = new LoginPage(page);
		const foldersPage = new PageContent(page, '/folders', 'Domains');

		await loginPage.goto();
		await loginPage.login(LoginPage.defaultEmail, LoginPage.defaultPassword);
		await foldersPage.goto();

		const folderRow = foldersPage.getRow(JOURNEY_FOLDER_NAME);
		const folderExists = await folderRow.isVisible();

		if (folderExists) {
			await foldersPage.deleteItemButton(JOURNEY_FOLDER_NAME).click();
			await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
			await foldersPage.deletePromptConfirmTextField().fill('yes');
			await foldersPage.deletePromptConfirmButton().click();
			await expect(foldersPage.getRow(JOURNEY_FOLDER_NAME)).not.toBeVisible();
		}

		await page.close();
	});
});
