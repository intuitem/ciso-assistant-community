import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('user can create representatives, solutions and entity assessments inside entity', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	entitiesPage,
	representativesPage,
	solutionsPage,
	usersPage,
	entityAssessmentsPage,
	librariesPage,
	complianceAssessmentsPage,
	page
}) => {
	await test.step('create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.hasUrl();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
		// NOTE: creating one more folder not to trip up the autocomplete test utils
		await foldersPage.createItem({
			name: vars.folderName + ' foo',
			description: vars.description
		});
	});

	await test.step('create required perimeter', async () => {
		await perimetersPage.goto();
		await perimetersPage.hasUrl();
		await perimetersPage.createItem({
			name: vars.perimeterName,
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.1234',
			lc_status: 'Production'
		});
		await perimetersPage.createItem({
			name: vars.perimeterName + ' bar',
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.12345',
			lc_status: 'Production'
		});
	});

	await test.step('import framework', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.framework.name, vars.framework.urn);
	});

	await test.step('create entity', async () => {
		await entitiesPage.goto();
		await entitiesPage.hasUrl();
		await entitiesPage.createItem(testObjectsData.entitiesPage.build);
		await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);
	});

	await test.step('create solution', async () => {
		await page.getByRole('tab', { name: 'Solutions' }).click();
		await expect(page.getByTestId('tabs-panel').getByText('Associated solutions')).toBeVisible();
		await solutionsPage.createItem(
			{
				name: 'Test solution'
			},
			undefined,
			undefined,
			'solution'
		);
	});

	await test.step('create representative', async () => {
		await page.getByRole('tab', { name: 'Representatives' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated representatives')
		).toBeVisible();
		await representativesPage.createItem(
			{
				email: 'john.doe@example.com',
				entity: testObjectsData.entitiesPage.build.name,
				create_user: true
			},
			undefined,
			undefined,
			'representative'
		);
	});

	await test.step('verify that user was created alongside representative', async () => {
		await page.getByRole('tab', { name: 'Representatives' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated representatives')
		).toBeVisible();
		await representativesPage.viewItemDetail('john.doe@example.com');
		await expect(page.getByTestId('user-field-value')).not.toBeEmpty();
		await page.getByTestId('user-field-value').locator('a').first().click();
		await usersPage.hasUrl();
		await usersPage.hasTitle('john.doe@example.com');
	});

	await test.step('go back to entity detail', async () => {
		await entitiesPage.goto();
		await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);
	});

	await test.step('create entity assessment', async () => {
		await page.getByRole('tab', { name: 'Entity assessments' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated entity assessments')
		).toBeVisible();
		await entityAssessmentsPage.createItem(
			{
				name: 'Test entity assessment',
				perimeter: vars.perimeterName,
				create_audit: true,
				framework: vars.framework.name
			},
			undefined,
			undefined,
			'entity assessment'
		);
	});

	await test.step('verify that user was redirected to newly created entity assessment', async () => {
		await entityAssessmentsPage.hasUrl();
		await entityAssessmentsPage.hasTitle('Test entity assessment');
	});

	await test.step('check that audit was created', async () => {
		await expect(page.getByTestId('compliance-assessment-field-value')).not.toBeEmpty();
		await page.getByTestId('compliance-assessment-field-value').locator('a').first().click();
		await complianceAssessmentsPage.hasUrl();
		await complianceAssessmentsPage.hasTitle('Test entity assessment');
	});
});

test.afterAll('cleanup', async ({ browser }) => {
	const page = await browser.newPage();
	const loginPage = new LoginPage(page);
	const foldersPage = new PageContent(page, '/folders', 'Domains');

	await loginPage.goto();
	await loginPage.login();
	await foldersPage.goto();

	await foldersPage.deleteItemButton(vars.folderName).click();
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();

	await foldersPage.deleteItemButton(vars.folderName + ' foo').click();
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();

	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
