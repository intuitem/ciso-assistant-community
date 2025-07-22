import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

const escalationThresholdsData = {
	displayName: 'Escalation thresholds',
	modelName: 'escalationthreshold',
	build: {
		point_in_time: { days: 1, hours: 1, minutes: 30 },
		qualifications: ['confidentiality', 'integrity', 'availability'],
		quali_impact: 'High',
		justification: 'Commodo adipisicing cillum labore ullamco ad id dolore reprehenderit.'
	}
};

test('user can create asset assessments inside BIA', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	assetsPage,
	librariesPage,
	businessImpactAnalysisPage,
	assetAssessmentsPage,
	escalationThresholdsPage,
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

	await test.step('create required assets', async () => {
		await assetsPage.goto();
		await assetsPage.hasUrl();
		await assetsPage.createItem({
			name: vars.assetName,
			description: vars.description,
			folder: vars.folderName,
			type: 'Primary'
		});
		// NOTE: creating one more asset not to trip up the autocomplete test utils
		await assetsPage.createItem({
			name: vars.assetName + ' foo',
			description: vars.description,
			folder: vars.folderName,
			type: 'Primary'
		});
	});

	await test.step('import risk matrix', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.matrix.name, vars.matrix.urn);
	});

	await test.step('create business impact analysis', async () => {
		await businessImpactAnalysisPage.goto();
		await businessImpactAnalysisPage.hasUrl();
		await businessImpactAnalysisPage.createItem(testObjectsData.businessImpactAnalysisPage.build);
	});

	await test.step('create asset assessment', async () => {
		await businessImpactAnalysisPage.viewItemDetail(
			testObjectsData.businessImpactAnalysisPage.build.name
		);
		await assetAssessmentsPage.createItem({ asset: vars.assetName }, undefined, page);
	});

	await test.step('check that asset assessment is created', async () => {
		await businessImpactAnalysisPage.getRow(vars.assetName).click();
		await assetAssessmentsPage.hasUrl();
	});

	await test.step('create escalation threshold', async () => {
		await escalationThresholdsPage.createItem(escalationThresholdsData.build);
	});

	await test.step('check that escalation threshold is created', async () => {
		await expect(
			assetAssessmentsPage.getRow(escalationThresholdsData.build.quali_impact)
		).toBeVisible();
	});

	await test.step('check that line heatmap has been updated', async () => {
		await expect(page.getByTestId('line-heatmap')).toContainText(
			escalationThresholdsData.build.quali_impact
		);
	});

	await test.step('delete escalation threshold', async () => {
		await assetAssessmentsPage
			.deleteItemButton(escalationThresholdsData.build.quali_impact)
			.click();
		await assetAssessmentsPage.deleteModalConfirmButton.click();
		await expect(
			assetAssessmentsPage.getRow(escalationThresholdsData.build.quali_impact)
		).not.toBeVisible();
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
