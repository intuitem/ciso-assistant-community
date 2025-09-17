import { m } from '$paraglide/messages.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { expect, test, TestContent, type Locator } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData = TestContent.itemBuilder(vars);

async function redirectToAnalytics(page) {
	const analyticsPage = new PageContent(page, '/analytics', 'Analytics');
	await analyticsPage.goto();
}

test.skip('Analytics full flow - creation, validation and cleanup', async ({
	page,
	logedPage,
	foldersPage,
	perimetersPage,
	appliedControlsPage,
	complianceAssessmentsPage,
	evidencesPage,
	riskAssessmentsPage,
	librariesPage
}) => {
	await test.step('Create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
	});

	await test.step('Create perimeter', async () => {
		await perimetersPage.goto();
		await perimetersPage.createItem({
			name: vars.perimeterName,
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'PERIM.001',
			lc_status: 'Production'
		});
	});

	await test.step('Create various controls', async () => {
		await appliedControlsPage.goto();

		const controls = [
			{ name: 'test-control-1', status: 'active' },
			{ name: 'test-control-2', status: 'deprecated', eta: '2023-11-11' },
			{ name: 'test-control-3', status: 'to_do' },
			{ name: 'test-control-4', status: 'on_hold' },
			{ name: 'test-control-5', status: 'in_progress' }
		];

		for (const control of controls) {
			const { eta, ...rest } = control;
			await appliedControlsPage.createItem({
				...rest,
				folder: vars.folderName,
				...(eta ? { eta } : {})
			});
		}
	});

	await test.step('Import a library', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();

		await librariesPage.importLibrary(
			'International standard ISO/IEC 27001:2022',
			undefined,
			'any'
		);

		await librariesPage.importLibrary('NIST CSF v2.0', undefined, 'any');

		await librariesPage.tab('Libraries store').click();
		await expect(librariesPage.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();
	});

	await test.step('Create audits', async () => {
		await complianceAssessmentsPage.goto();
		await complianceAssessmentsPage.createItem({
			name: 'test-audit-1',
			framework: 'NIST CSF v2.0',
			authors: ['admin@tests.com'],
			perimeter: `${vars.folderName}/${vars.perimeterName}`
		});
		await complianceAssessmentsPage.goto();
		await complianceAssessmentsPage.createItem({
			name: 'test-audit-2',
			authors: ['admin@tests.com'],
			framework: 'International standard ISO/IEC 27001:2022',
			perimeter: `${vars.folderName}/${vars.perimeterName}`
		});
	});

	await test.step('Create evidence', async () => {
		await evidencesPage.goto();
		await evidencesPage.createItem({
			name: vars.evidenceName,
			description: vars.description,
			folder: vars.folderName
		});
	});

	await test.step('Import a risk matrix', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();

		await librariesPage.importLibrary('4x4 risk matrix from EBIOS-RM', undefined, 'any');

		await librariesPage.tab('Libraries store').click();
		await expect(librariesPage.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();
	});

	await test.step('Create risk assessment', async () => {
		await riskAssessmentsPage.goto();
		await riskAssessmentsPage.createItem({
			name: 'test-risk-assessment',
			perimeter: `${vars.folderName}/${vars.perimeterName}`
		});
	});

	await test.step('Verify data view in analytics', async () => {
		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-analytics').click();
		await expect(page.locator('#page-title')).toHaveText('Analytics');
		await expect(page).toHaveURL('/analytics');

		await expect(page.getByTestId('card-controls-total')).toHaveText('5');
		await expect(page.getByTestId('card-controls-active')).toHaveText('1');
		await expect(page.getByTestId('card-controls-deprecated')).toHaveText('1');
		await expect(page.getByTestId('card-controls-to do')).toHaveText('1');
		await expect(page.getByTestId('card-controls-in progress')).toHaveText('1');
		await expect(page.getByTestId('card-controls-on hold')).toHaveText('1');
		await expect(page.getByTestId('card-controls-Missed ETA')).toHaveText('1');

		await expect(page.getByText('test-audit-1')).toBeVisible();
		await expect(page.getByText('test-audit-2')).toBeVisible();

		await expect(page.getByTestId('card-compliance-Used frameworks')).toHaveText('2');
		await expect(page.getByTestId('card-compliance-Evidences')).toHaveText('1');
		await expect(page.getByTestId('card-risk-Assessments')).toHaveText('1');

		const analyticsPage = new PageContent(page, '/analytics?tab=governance', 'Analytics');
		await analyticsPage.goto();
		await expect(page.getByTestId('card-Applied controls')).toHaveText('5');
		await expect(page.getByTestId('card-Risk assessments')).toHaveText('1');
		await expect(page.getByTestId('card-Audits')).toHaveText('2');
		await expect(page.getByText('NIST CSF v2.0')).toBeVisible();
		await expect(page.getByText('International standard ISO/IEC 27001:2022')).toBeVisible();
		await expect(page.getByText('test-control-2')).toBeVisible();
	});

	await test.step('Verify redirection in analytics', async () => {
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-total')).toBeVisible();
		await page.getByTestId('card-controls-total').click();
		await expect(page).toHaveURL('/applied-controls');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-active')).toBeVisible();
		await page.getByTestId('card-controls-active').click();
		await expect(page).toHaveURL('/applied-controls?status=active');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-deprecated')).toBeVisible();
		await page.getByTestId('card-controls-deprecated').click();
		await expect(page).toHaveURL('/applied-controls?status=deprecated');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-to do')).toBeVisible();
		await page.getByTestId('card-controls-to do').click();
		await expect(page).toHaveURL('/applied-controls?status=to_do');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-in progress')).toBeVisible();
		await page.getByTestId('card-controls-in progress').click();
		await expect(page).toHaveURL('/applied-controls?status=in_progress');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-controls-on hold')).toBeVisible();
		await page.getByTestId('card-controls-on hold').click();
		await expect(page).toHaveURL('/applied-controls?status=on_hold');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-compliance-Used frameworks')).toBeVisible();
		await page.getByTestId('card-compliance-Used frameworks').click();
		await expect(page).toHaveURL('/frameworks');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-compliance-Evidences')).toBeVisible();
		await page.getByTestId('card-compliance-Evidences').click();
		await expect(page).toHaveURL('/evidences');
		await redirectToAnalytics(page);

		await expect(page.getByTestId('card-risk-Assessments')).toBeVisible();
		await page.getByTestId('card-risk-Assessments').click();
		await expect(page).toHaveURL('/risk-assessments');
		await redirectToAnalytics(page);
	});
});

test.skip('cleanup', async ({ browser }) => {
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

	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
