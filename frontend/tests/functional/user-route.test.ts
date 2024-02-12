import { dirname, join } from 'path';
import { test, expect, httpResponsesListener, getUniqueValue as _ } from '../utils/test-utils';
import { fileURLToPath } from 'url';

const testVars = {
	assessmentName: _('Test assessment'),
	assetName: _('Test asset'),
	evidenceName: _('Test evidence'),
	folderName: _('Test folder'),
	projectName: _('Test project'),
	riskAcceptanceName: _('Test risk acceptance'),
	riskAnalysisName: _('Test risk analysis'),
	riskScenarioName: _('Test risk scenario'),
	securityFunctionName: _('Test security function'),
	securityMeasureName: _('Test security measure'),
	threatName: _('Test threat'),
	description: 'Test description',
	file: new URL('../utils/test_image.jpg', import.meta.url).pathname,
	framework: {
		name: 'NIS 2 requirements',
		urn: 'urn:intuitem:risk:library:nis2'
	},
	riskMatrix: {
		name: 'Critical risk matrix 5x5',
		displayName: 'default_5x5',
		urn: 'urn:intuitem:risk:library:critical_risk_matrix_5x5'
	},
	securityFunction: {
		name: 'Physical security policy',
		urn: 'urn:intuitem:risk:function:POL.PHYSICAL'
	},
	threat: {
		name: 'T1052 - Exfiltration Over Physical Medium',
		urn: 'urn:intuitem:risk:threat:T1052'
	}
};

test('user usual routine actions are working correctly', async ({
	logedPage,
	pages,
	analyticsPage: analyticsPage,
	sideBar,
	page
}) => {
	test.slow();

	await test.step('proper redirection to the analytics page after login', async () => {
		await analyticsPage.hasUrl();
		await analyticsPage.hasTitle();
		httpResponsesListener(page);
	});

	await test.step('user can create a domain', async () => {
		await sideBar.click('General', pages.foldersPage.url);
		await expect(page).toHaveURL(pages.foldersPage.url);
		await pages.foldersPage.hasTitle();

		await pages.foldersPage.createItem({
			name: testVars.folderName,
			description: testVars.description
		});

		//TODO assert that the folder data are displayed in the table
	});

	await test.step('user can create a project', async () => {
		await sideBar.click('General', pages.projectsPage.url);
		await expect(page).toHaveURL(pages.projectsPage.url);
		await pages.projectsPage.hasTitle();

		await pages.projectsPage.createItem({
			name: testVars.projectName,
			description: testVars.description,
			folder: testVars.folderName,
			internal_reference: 'Test internal reference',
			lc_status: 'Production'
		});

		//TODO assert that the project data are displayed in the table
	});

	await test.step('user can create an asset', async () => {
		await sideBar.click('General', pages.assetsPage.url);
		await expect(page).toHaveURL(pages.assetsPage.url);
		await pages.assetsPage.hasTitle();

		await pages.assetsPage.createItem({
			name: testVars.assetName,
			description: testVars.description,
			business_value: 'Test value',
			folder: testVars.folderName,
			type: 'Primary'
		});

		//TODO assert that the asset data are displayed in the table
	});

	await test.step('user can import a framework', async () => {
		await sideBar.click('Compliance management', pages.frameworksPage.url);
		await expect(page).toHaveURL(pages.frameworksPage.url);
		await pages.frameworksPage.hasTitle();

		await pages.frameworksPage.addButton.click();
		await expect(page).toHaveURL(pages.librariesPage.url);
		await pages.librariesPage.hasTitle();

		await pages.librariesPage.importLibrary(testVars.framework.name, testVars.framework.urn);

		await sideBar.click('Compliance management', pages.frameworksPage.url);
		await expect(page).toHaveURL(pages.frameworksPage.url);
		await expect(page.getByRole('row', { name: testVars.framework.name })).toBeVisible();
	});

	await test.step('user can create a security function', async () => {
		await sideBar.click('General', pages.securityFunctionsPage.url);
		await expect(page).toHaveURL(pages.securityFunctionsPage.url);
		await pages.securityFunctionsPage.hasTitle();

		await pages.securityFunctionsPage.createItem({
			name: testVars.securityFunctionName,
			description: testVars.description,
			provider: 'Test provider',
			folder: testVars.folderName
		});

		//TODO assert that the security function data are displayed in the table
	});

	await test.step('user can create a security measure', async () => {
		await sideBar.click('General', pages.securityMeasuresPage.url);
		await expect(page).toHaveURL(pages.securityMeasuresPage.url);
		await pages.securityMeasuresPage.hasTitle();

		await pages.securityMeasuresPage.createItem({
			name: testVars.securityMeasureName,
			description: testVars.description,
			type: 'Technical',
			status: 'In progress',
			eta: '2025-01-01',
			link: 'https://intuitem.com/',
			effort: 'Large',
			folder: testVars.folderName,
			security_function: testVars.securityFunction.name
		});

		//TODO assert that the security measure data are displayed in the table
	});

	await test.step('user can create an assessment', async () => {
		await sideBar.click('Compliance management', pages.assessmentsPage.url);
		await expect(page).toHaveURL(pages.assessmentsPage.url);
		await pages.assessmentsPage.hasTitle();

		await pages.assessmentsPage.createItem({
			name: testVars.assessmentName,
			description: testVars.description,
			project: testVars.projectName,
			framework: testVars.framework.name,
			version: '1.4.2',
			is_draft: 'false',
			is_obsolete: 'true'
		});

		//TODO assert that the assessment data are displayed in the table
	});

	await test.step('user can create an evidence', async () => {
		await sideBar.click('Compliance management', pages.evidencesPage.url);
		await expect(page).toHaveURL(pages.evidencesPage.url);
		await pages.evidencesPage.hasTitle();

		await pages.evidencesPage.createItem({
			name: testVars.evidenceName,
			description: testVars.description,
			attachment: testVars.file,
			security_measure: testVars.securityMeasureName,
			comment: 'Test comment'
		});

		//TODO assert that the evidence data are displayed in the table
	});

	await test.step('user can import a risk matrix', async () => {
		await sideBar.click('Risk management', pages.riskMatricesPage.url);
		await expect(page).toHaveURL(pages.riskMatricesPage.url);
		await pages.riskMatricesPage.hasTitle();

		await pages.riskMatricesPage.addButton.click();
		await expect(page).toHaveURL(pages.librariesPage.url);
		await pages.librariesPage.hasTitle();

		await pages.librariesPage.importLibrary(testVars.matrix.name, testVars.matrix.urn);

		await sideBar.click('Risk management', pages.riskMatricesPage.url);
		await expect(page).toHaveURL(pages.riskMatricesPage.url);
		await expect(page.getByRole('row', { name: testVars.matrix.displayName })).toBeVisible();
		// await expect(page.getByRole('row', { name: testVars.matrix.name })).toBeVisible();
	});

	await test.step('user can create a risk analysis', async () => {
		await sideBar.click('Risk management', pages.riskAnalysesPage.url);
		await expect(page).toHaveURL(pages.riskAnalysesPage.url);
		await pages.riskAnalysesPage.hasTitle();

		await pages.riskAnalysesPage.createItem({
			name: testVars.riskAnalysisName,
			description: testVars.description,
			project: testVars.projectName,
			version: '1.4.2',
			is_draft: 'false',
			auditor: logedPage.email,
			risk_matrix: testVars.matrix.displayName
		});

		//TODO assert that the risk analysis data are displayed in the table
	});

	await test.step('user can create a threat', async () => {
		await sideBar.click('General', pages.threatsPage.url);
		await expect(page).toHaveURL(pages.threatsPage.url);
		await pages.threatsPage.hasTitle();

		await pages.threatsPage.createItem({
			name: testVars.threatName,
			description: testVars.description,
			folder: testVars.folderName,
			provider: 'Test provider'
		});

		//TODO assert that the threat data are displayed in the table
	});

	await test.step('user can create a risk scenario', async () => {
		await sideBar.click('Risk management', pages.riskScenariosPage.url);
		await expect(page).toHaveURL(pages.riskScenariosPage.url);
		await pages.riskScenariosPage.hasTitle();

		await pages.riskScenariosPage.createItem({
			name: testVars.riskScenarioName,
			description: testVars.description,
			analysis: testVars.riskAnalysisName,
			threat: testVars.threat.name
		});

		//TODO assert that the risk scenario data are displayed in the table
	});

	await test.step('user can create a risk acceptance', async () => {
		await sideBar.click('Risk management', pages.riskAcceptancesPage.url);
		await expect(page).toHaveURL(pages.riskAcceptancesPage.url);
		await pages.riskAcceptancesPage.hasTitle();

		await pages.riskAcceptancesPage.createItem({
			name: testVars.riskAcceptanceName,
			description: testVars.description,
			expiry_date: '2025-01-01',
			justification: 'Test comment',
			folder: testVars.folderName,
			approver: logedPage.email,
			risk_scenarios: testVars.riskScenarioName
		});

		//TODO assert that the risk acceptance data are displayed in the table
	});

	await test.step('cleanup', async () => {
		//clean up test folder and associated objects
		await sideBar.click('General', pages.foldersPage.url);
		await expect(pages.foldersPage.deleteItemButton(testVars.folderName)).toBeVisible();
		await pages.foldersPage.deleteItemButton(testVars.folderName).click();
		await pages.foldersPage.deleteModalConfirmButton.click();
		await expect(pages.foldersPage.deleteModalTitle).not.toBeVisible();

		// //clean up test framework
		// await sideBar.click("Compliance management", pages.frameworksPage.url);
		// await expect(pages.frameworksPage.deleteItemButton(testVars.framework.name)).toBeVisible();
		// await pages.frameworksPage.deleteItemButton(testVars.framework.name).click();
		// await pages.frameworksPage.deleteModalConfirmButton.click();
		// await expect(pages.frameworksPage.deleteModalTitle).not.toBeVisible();

		// //clean up test risk matrix
		// await sideBar.click("Risk management", pages.riskMatricesPage.url);
		// await expect(pages.riskMatricesPage.deleteItemButton(testVars.matrix.displayName)).toBeVisible();
		// await pages.riskMatricesPage.deleteItemButton(testVars.matrix.displayName).click();
		// await pages.riskMatricesPage.deleteModalConfirmButton.click();
		// await expect(pages.riskMatricesPage.deleteModalTitle).not.toBeVisible();
	});
});
