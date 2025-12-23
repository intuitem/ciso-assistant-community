import { LoginPage } from '../../../utils/login-page.js';
import { TestContent, test, expect, type Page } from '../../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test.describe.configure({ mode: 'serial' });

test.describe('General settings', () => {
	let page: Page;
	test.beforeAll(async ({ browser }) => {
		// Create a unique page to use for all the tests on this user group and login
		page = await browser.newPage();
		const loginPage = new LoginPage(page);
		await loginPage.goto();
		await loginPage.login(LoginPage.defaultEmail, LoginPage.defaultPassword);
		await expect(page).toHaveURL('/analytics');
	});

	test.use({
		page: async ({}, use) => {
			await use(page);
		}
	});

	test.beforeAll(async ({ foldersPage, librariesPage, page }) => {
		await test.step('create required folder', async () => {
			await foldersPage.goto();
			await foldersPage.hasUrl();
			await foldersPage.createItem({
				name: vars.folderName,
				description: vars.description
			});
		});
		await test.step('import risk matrix', async () => {
			await librariesPage.goto();
			await librariesPage.hasUrl();
			await librariesPage.importLibrary(vars.matrix.name, vars.matrix.urn);
		});
	});
	test.beforeEach(async ({ settingsPage, page }) => {
		await settingsPage.goto();
		await settingsPage.hasUrl();
		await settingsPage.hasTitle();
	});

	test('risk matrices settings', async ({ riskMatricesPage, settingsPage }) => {
		await test.step('check default matrix disposition', async () => {
			await page.getByRole('button', { name: ' Risk matrix settings +' }).click();
			await expect(page.getByTestId('form-input-risk-matrix-swap-axes')).not.toBeChecked();
			await expect(page.getByTestId('form-input-risk-matrix-flip-vertical')).not.toBeChecked();

			await riskMatricesPage.goto();
			await riskMatricesPage.viewItemDetail(vars.matrix.name);
			await expect(page.getByTestId('y-label')).toHaveText('Likelihood');
			await expect(page.getByTestId('x-label')).toHaveText('Impact');
			await expect(page.getByTestId('x-label-flipped')).not.toBeVisible();
		});

		await test.step('test swap axes', async () => {
			await settingsPage.goto();
			await settingsPage.hasUrl();
			await settingsPage.hasTitle();
			await page.getByRole('button', { name: ' Risk matrix settings +' }).click();
			await page.getByTestId('form-input-risk-matrix-swap-axes').check();
			await page.getByRole('button', { name: 'Save' }).click();
			const toast = page.getByTestId('toast');
			await expect(toast).toBeVisible();

			await riskMatricesPage.goto();
			await riskMatricesPage.viewItemDetail(vars.matrix.name);
			await expect(page.getByTestId('y-label')).toHaveText('Impact');
			await expect(page.getByTestId('x-label')).toHaveText('Likelihood');
			await expect(page.getByTestId('x-label-flipped')).not.toBeVisible();
		});

		await test.step('test flip vertical', async () => {
			await settingsPage.goto();
			await settingsPage.hasUrl();
			await settingsPage.hasTitle();
			await page.getByRole('button', { name: ' Risk matrix settings +' }).click();
			await page.getByTestId('form-input-risk-matrix-flip-vertical').check();
			await page.getByRole('button', { name: 'Save' }).click();
			const toast = page.getByTestId('toast');
			await expect(toast).toBeVisible();

			await riskMatricesPage.goto();
			await riskMatricesPage.viewItemDetail(vars.matrix.name);
			await expect(page.getByTestId('y-label')).toHaveText('Impact');
			await expect(page.getByTestId('x-label')).not.toBeVisible();
			await expect(page.getByTestId('x-label-flipped')).toHaveText('Likelihood');
			await expect(page.getByTestId('x-label-flipped')).toBeVisible();
		});

		await test.step('test change labels', async () => {
			await settingsPage.goto();
			await settingsPage.hasUrl();
			await settingsPage.hasTitle();
			await page.getByRole('button', { name: ' Risk matrix settings +' }).click();
			await page.getByLabel('Risk matrix settings −').getByText('Ebios RM').click();
			await page.getByRole('button', { name: 'Save' }).click();
			const toast = page.getByTestId('toast');
			await expect(toast).toBeVisible();

			await riskMatricesPage.goto();
			await riskMatricesPage.viewItemDetail(vars.matrix.name);
			await expect(page.getByTestId('y-label')).toHaveText('Severity');
			await expect(page.getByTestId('x-label-flipped')).toHaveText('Likelihood');
		});
	});

	test('assets settings', async ({ assetsPage, settingsPage }) => {
		await test.step('security targets scales', async () => {
			await test.step('1-4', async () => {
				await page.getByRole('button', { name: ' Assets +' }).click();
				await expect(page.getByTestId('form-input-security-objective-scale')).toHaveValue('1-4');
				await page.getByRole('button', { name: 'Save' }).click();
				await expect(page.getByTestId('toast')).toBeVisible();
				await page.getByTestId('sidebar').getByRole('button', { name: 'Risk' }).click();

				await assetsPage.goto();
				await assetsPage.hasTitle();
				await page.getByTestId('add-button').click();
				await page.getByRole('button', { name: ' Security targets' }).click();
				await expect(page.locator('.text-base').first()).toHaveText('1');
				await expect(page.locator('label:nth-child(4) > .text-base').first()).toHaveText('4');
				await page.getByTestId('cancel-button').click();
			});

			await test.step('0-4', async () => {
				await settingsPage.goto();
				await settingsPage.hasTitle();
				await page.getByRole('button', { name: ' Assets +' }).click();
				await page.getByTestId('form-input-security-objective-scale').selectOption('0-4');
				await page.getByRole('button', { name: 'Save' }).click();
				await expect(page.getByTestId('toast')).toBeVisible();
				await assetsPage.goto();
				await assetsPage.hasTitle();
				await page.getByTestId('add-button').click();
				await page.getByRole('button', { name: ' Security targets' }).click();
				await expect(page.locator('.text-base').first()).toHaveText('0');
				await expect(page.locator('label:nth-child(5) > .text-base').first()).toHaveText('4');
				await page.getByTestId('cancel-button').click();
			});

			await test.step('1-5', async () => {
				await settingsPage.goto();
				await settingsPage.hasTitle();
				await page.getByRole('button', { name: ' Assets +' }).click();
				await page.getByTestId('form-input-security-objective-scale').selectOption('1-5');
				await page.getByRole('button', { name: 'Save' }).click();
				await expect(page.getByTestId('toast')).toBeVisible();
				await assetsPage.goto();
				await assetsPage.hasTitle();
				await page.getByTestId('add-button').click();
				await page.getByRole('button', { name: ' Security targets' }).click();
				await expect(page.locator('.text-base').first()).toHaveText('1');
				await expect(page.locator('label:nth-child(5) > .text-base').first()).toHaveText('5');
				await page.getByTestId('cancel-button').click();
			});

			await test.step('0-3', async () => {
				await settingsPage.goto();
				await settingsPage.hasTitle();
				await page.getByRole('button', { name: ' Assets +' }).click();
				await page.getByTestId('form-input-security-objective-scale').selectOption('0-3');
				await page.getByRole('button', { name: 'Save' }).click();
				await expect(page.getByTestId('toast')).toBeVisible();
				await assetsPage.goto();
				await assetsPage.hasTitle();
				await page.getByTestId('add-button').click();
				await page.getByRole('button', { name: ' Security targets' }).click();
				await expect(page.locator('.text-base').first()).toHaveText('0');
				await expect(page.locator('label:nth-child(4) > .text-base').first()).toHaveText('3');
				await page.getByTestId('cancel-button').click();
			});

			await test.step('FIPS-199', async () => {
				await settingsPage.goto();
				await settingsPage.hasTitle();
				await page.getByRole('button', { name: ' Assets +' }).click();
				await page.getByTestId('form-input-security-objective-scale').selectOption('FIPS-199');
				await page.getByRole('button', { name: 'Save' }).click();
				await expect(page.getByTestId('toast')).toBeVisible();
				await assetsPage.goto();
				await assetsPage.hasTitle();
				await page.getByTestId('add-button').click();
				await page.getByRole('button', { name: ' Security targets' }).click();
				await expect(page.locator('.text-base').first()).toHaveText('low');
				await expect(page.locator('label:nth-child(2) > .text-base').first()).toHaveText(
					'moderate'
				);
				await expect(page.locator('label:nth-child(3) > .text-base').first()).toHaveText('high');
				await page.getByTestId('cancel-button').click();
			});
		});
	});
});
