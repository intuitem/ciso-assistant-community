import { LoginPage } from '../../utils/login-page.js';
import { TestContent, test, expect, type Page } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test.describe.configure({ mode: 'serial' });

test.describe('Privacy basic actions', () => {
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
		page: async (_, use) => {
			await use(page);
		}
	});

	test.beforeAll(async ({ foldersPage, processingsPage, page }) => {
		await test.step('create required folder', async () => {
			await foldersPage.goto();
			await foldersPage.hasUrl();
			await foldersPage.createItem({
				name: vars.folderName,
				description: vars.description
			});
		});
		await test.step('create required processing', async () => {
			await processingsPage.goto();
			await processingsPage.hasUrl();
			await processingsPage.createItem(testObjectsData.processingsPage.build);
		});
	});
	test.beforeEach(async ({ processingsPage, page }) => {
		await processingsPage.goto();
		await processingsPage.hasUrl();
		await processingsPage.viewItemDetail(testObjectsData.processingsPage.build.name);
	});

	test('user can create personal data inside processing', async ({ personalDataPage, page }) => {
		await test.step('create personal data', async () => {
			await page.getByRole('tab', { name: 'Personal Data' }).click();
			await expect(
				page.getByTestId('tabs-panel').getByText('Associated personal data')
			).toBeVisible();
			const { processing, ...personalData } = testObjectsData.personalDataPage.build;
			await personalDataPage.createItem(personalData, undefined, undefined, 'personal data');
		});
	});

	test('user can create data subject inside processing', async ({ dataSubjectsPage, page }) => {
		await test.step('create data subject', async () => {
			await page.getByRole('tab', { name: 'Data Subject' }).click();
			await expect(
				page.getByTestId('tabs-panel').getByText('Associated data subject')
			).toBeVisible();
			const { processing, ...dataSubject } = testObjectsData.dataSubjectsPage.build;
			await dataSubjectsPage.createItem(dataSubject, undefined, undefined, 'data subject');
		});
	});

	test('user can create purpose inside processing', async ({ purposesPage, page }) => {
		await test.step('create purpose', async () => {
			await page.getByRole('tab', { name: 'Purposes' }).click();
			await expect(page.getByTestId('tabs-panel').getByText('Associated purposes')).toBeVisible();
			const { processing, ...purpose } = testObjectsData.purposesPage.build;
			await purposesPage.createItem(purpose, undefined, undefined, 'purpose');
		});
	});

	test('user can create data recipient inside processing', async ({ dataRecipientsPage, page }) => {
		await test.step('create data recipient', async () => {
			await page.getByRole('tab', { name: 'Data Recipients' }).click();
			await expect(
				page.getByTestId('tabs-panel').getByText('Associated data recipients')
			).toBeVisible();
			const { processing, ...dataRecipient } = testObjectsData.dataRecipientsPage.build;
			await dataRecipientsPage.createItem(dataRecipient, undefined, undefined, 'data recipient');
		});
	});

	test('user can create data contractor inside processing', async ({
		dataContractorsPage,
		page
	}) => {
		await test.step('create data contractor', async () => {
			await page.getByRole('tab', { name: 'Data Contractors' }).click();
			await expect(
				page.getByTestId('tabs-panel').getByText('Associated data contractors')
			).toBeVisible();
			const { processing, ...datacontractor } = testObjectsData.dataContractorsPage.build;
			await dataContractorsPage.createItem(datacontractor, undefined, undefined, 'data contractor');
		});
	});

	test('user can create data transfer inside processing', async ({ dataTransfersPage, page }) => {
		await test.step('create data transfer', async () => {
			await page.getByRole('tab', { name: 'Data Transfers' }).click();
			await expect(
				page.getByTestId('tabs-panel').getByText('Associated data transfers')
			).toBeVisible();
			const { processing, ...dataTransfer } = testObjectsData.dataTransfersPage.build;
			await dataTransfersPage.createItem(dataTransfer, undefined, undefined, 'data transfer');
		});
	});
});
