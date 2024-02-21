import { LoginPage } from '../utils/login-page.js';
import { test, expect, setHttpResponsesListener, TestContent } from '../utils/test-utils.js';

const vars = TestContent.generateTestVars();

test('user usual routine actions are working correctly', async ({
	logedPage,
	pages,
	analyticsPage: overviewPage,
	sideBar,
	page
}) => {
	test.slow();

	await test.step('proper redirection to the overview page after login', async () => {
		await overviewPage.hasUrl();
		await overviewPage.hasTitle();
		setHttpResponsesListener(page);
	});

	await test.step('user can create a domain', async () => {
		await sideBar.click('Organization', pages.foldersPage.url);
		await expect(page).toHaveURL(pages.foldersPage.url);
		await pages.foldersPage.hasTitle();

		await pages.foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});

		//TODO assert that the domain data are displayed in the table
	});

	await test.step('user can create a project', async () => {
		await sideBar.click('Organization', pages.projectsPage.url);
		await expect(page).toHaveURL(pages.projectsPage.url);
		await pages.projectsPage.hasTitle();

		await pages.projectsPage.createItem({
			name: vars.projectName,
			description: vars.description,
			folder: vars.folderName,
			internal_reference: 'Test internal reference',
			lc_status: 'Production'
		});

		//TODO assert that the project data are displayed in the table
	});

	await test.step('user can create an asset', async () => {
		await sideBar.click('Context', pages.assetsPage.url);
		await expect(page).toHaveURL(pages.assetsPage.url);
		await pages.assetsPage.hasTitle();

		await pages.assetsPage.createItem({
			name: vars.assetName,
			description: vars.description,
			business_value: 'Test value',
			folder: vars.folderName,
			type: 'Primary'
		});

		//TODO assert that the asset data are displayed in the table
	});

	await test.step('user can import a framework', async () => {
		await sideBar.click('Compliance', pages.frameworksPage.url);
		await expect(page).toHaveURL(pages.frameworksPage.url);
		await pages.frameworksPage.hasTitle();

		await pages.frameworksPage.addButton.click();
		await expect(page).toHaveURL(pages.librariesPage.url);
		await pages.librariesPage.hasTitle();

		await pages.librariesPage.importLibrary(vars.framework.name, vars.framework.urn);

		await sideBar.click('Compliance', pages.frameworksPage.url);
		await expect(page).toHaveURL(pages.frameworksPage.url);
		await expect(page.getByRole('row', { name: vars.framework.name })).toBeVisible();
	});

	await test.step('user can create a security function', async () => {
		await sideBar.click('Context', pages.securityFunctionsPage.url);
		await expect(page).toHaveURL(pages.securityFunctionsPage.url);
		await pages.securityFunctionsPage.hasTitle();

		await pages.securityFunctionsPage.createItem({
			name: vars.securityFunctionName,
			description: vars.description,
			category: 'Physical',
			provider: 'Test provider',
			folder: vars.folderName
		});

		//TODO assert that the security function data are displayed in the table
	});

	await test.step('user can create a security measure', async () => {
		await sideBar.click('Context', pages.securityMeasuresPage.url);
		await expect(page).toHaveURL(pages.securityMeasuresPage.url);
		await pages.securityMeasuresPage.hasTitle();

		await pages.securityMeasuresPage.createItem({
			name: vars.securityMeasureName,
			description: vars.description,
			category: 'Technical',
			status: 'Planned',
			eta: '2025-01-01',
			link: 'https://intuitem.com/',
			effort: 'Large',
			folder: vars.folderName,
			security_function: vars.securityFunctionName
		});

		//TODO assert that the security measure data are displayed in the table
	});

	await test.step('user can create a compliance assessment', async () => {
		await sideBar.click('Compliance', pages.complianceAssessmentsPage.url);
		await expect(page).toHaveURL(pages.complianceAssessmentsPage.url);
		await pages.complianceAssessmentsPage.hasTitle();

		await pages.complianceAssessmentsPage.createItem({
			name: vars.assessmentName,
			description: vars.description,
			project: vars.projectName,
			version: '1.4.2',
			framework: vars.framework.name,
			eta: '2025-01-01',
			due_date: '2025-05-01'
		});

		//TODO assert that the compliance assessment data are displayed in the table
	});

	await test.step('user can create an evidence', async () => {
		await sideBar.click('Compliance', pages.evidencesPage.url);
		await expect(page).toHaveURL(pages.evidencesPage.url);
		await pages.evidencesPage.hasTitle();

		await pages.evidencesPage.createItem({
			name: vars.evidenceName,
			description: vars.description,
			attachment: vars.file,
			folder: vars.folderName,
			requirement_assessments: [
				vars.requirement_assessment.name,
				vars.requirement_assessment2.name
			],
			link: 'https://intuitem.com/'
		});

		//TODO assert that the evidence data are displayed in the table
	});

	await test.step('user can import a risk matrix', async () => {
		await sideBar.click('Governance', pages.riskMatricesPage.url);
		await expect(page).toHaveURL(pages.riskMatricesPage.url);
		await pages.riskMatricesPage.hasTitle();

		await pages.riskMatricesPage.addButton.click();
		await expect(page).toHaveURL(pages.librariesPage.url);
		await pages.librariesPage.hasTitle();

		await pages.librariesPage.importLibrary(vars.matrix.name, vars.matrix.urn);

		await sideBar.click('Governance', pages.riskMatricesPage.url);
		await expect(page).toHaveURL(pages.riskMatricesPage.url);
		await expect(page.getByRole('row', { name: vars.matrix.displayName })).toBeVisible();
	});

	await test.step('user can create a risk assessment', async () => {
		await sideBar.click('Risk', pages.riskAssessmentsPage.url);
		await expect(page).toHaveURL(pages.riskAssessmentsPage.url);
		await pages.riskAssessmentsPage.hasTitle();

		await pages.riskAssessmentsPage.createItem({
			name: vars.riskAssessmentName,
			description: vars.description,
			project: vars.projectName,
			version: '1.4.2',
			risk_matrix: vars.matrix.displayName,
			eta: '2025-01-01',
			due_date: '2025-05-01'
		});

		//TODO assert that the risk assessment data are displayed in the table
	});

	await test.step('user can create a threat', async () => {
		await sideBar.click('Context', pages.threatsPage.url);
		await expect(page).toHaveURL(pages.threatsPage.url);
		await pages.threatsPage.hasTitle();

		await pages.threatsPage.createItem({
			name: vars.threatName,
			description: vars.description,
			folder: vars.folderName,
			provider: 'Test provider'
		});

		//TODO assert that the threat data are displayed in the table
	});

	await test.step('user can create a risk scenario', async () => {
		await sideBar.click('Risk', pages.riskScenariosPage.url);
		await expect(page).toHaveURL(pages.riskScenariosPage.url);
		await pages.riskScenariosPage.hasTitle();

		await pages.riskScenariosPage.createItem({
			name: vars.riskScenarioName,
			description: vars.description,
			risk_assessment: vars.riskAssessmentName,
			threats: [vars.threatName]
		});

		//TODO assert that the risk scenario data are displayed in the table
	});

	await test.step('user can create a risk acceptance', async () => {
		await sideBar.click('Risk', pages.riskAcceptancesPage.url);
		await expect(page).toHaveURL(pages.riskAcceptancesPage.url);
		await pages.riskAcceptancesPage.hasTitle();

		await pages.riskAcceptancesPage.createItem({
			name: vars.riskAcceptanceName,
			description: vars.description,
			expiry_date: '2025-01-01',
			folder: vars.folderName,
			approver: LoginPage.defaultEmail,
			risk_scenarios: [vars.riskScenarioName]
		});

		//TODO assert that the risk acceptance data are displayed in the table
	});

	await test.step('user can add another user', async () => {
		await sideBar.click('Organization', pages.usersPage.url);
		await expect(page).toHaveURL(pages.usersPage.url);
		await pages.usersPage.hasTitle();

		await pages.usersPage.createItem({
			email: vars.user.email
		});

		//TODO assert that the user data are displayed in the table
	});
});

test.afterEach('cleanup', async ({ foldersPage, usersPage, page }) => {
	await foldersPage.goto();
	await page.waitForURL(foldersPage.url);
	await foldersPage.deleteItemButton(vars.folderName).click();
	await foldersPage.deleteModalConfirmButton.click();
	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();

	await usersPage.goto();
	await page.waitForURL(usersPage.url);
	await usersPage.deleteItemButton(vars.user.email).click();
	await usersPage.deleteModalConfirmButton.click();
	await expect(usersPage.getRow(vars.user.email)).not.toBeVisible();
});

