import { assigned, m, riskAssessment } from '$paraglide/messages.js';
import { version } from 'os';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { expect, test, TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData = TestContent.itemBuilder(vars);

test('My assignments full flow - creation, validation, negative case and cleanup', async ({
	page,
	logedPage,
	foldersPage,
	perimetersPage,
	appliedControlsPage,
	complianceAssessmentsPage,
	librariesPage,
	riskAssessmentsPage,
	riskScenariosPage,
	securityExceptionsPage
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
			folder: vars.folderName
		});
	});

	await test.step('Import a risk matrix', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();

		await librariesPage.importLibrary('4x4 risk matrix from EBIOS-RM', undefined, 'any');

		// Optional: Confirm import
		await librariesPage.tab('Libraries store').click();
		await expect(librariesPage.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();
	});

	await test.step('Create risk assessment', async () => {
		await riskAssessmentsPage.goto();
		await riskAssessmentsPage.createItem({
			name: 'test-risk-assessment',
			perimeter: `${vars.folderName}/${vars.perimeterName}`,
			version: '2.0',
			description: 'Hi from ciso-assistant dev'
		});
		await riskAssessmentsPage.goto();

		const riskRow = page.getByRole('row', { name: /test-risk-assessment/i });
		await riskRow.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create security exception', async () => {
		await securityExceptionsPage.goto();
		await securityExceptionsPage.createItem({
			name: 'test-security-exception',
			folder: vars.folderName
		});
		await securityExceptionsPage.goto();

		const riskRow = page.getByRole('row', { name: /test-security-exception/i });
		await riskRow.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-owners').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create risk scenario', async () => {
		await riskScenariosPage.goto();
		await riskScenariosPage.createItem({
			name: 'test-risk-scenario',
			riskAssessment: 'test-risk-assessment',
			description: 'Hi from ciso-assistant dev',
			ref_id: 'R.1234'
		});
		await riskScenariosPage.goto();

		const riskRow = page.getByRole('row', { name: /test-risk-scenario/i });
		await riskRow.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-owner').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Create control with owner', async () => {
		await appliedControlsPage.goto();
		await appliedControlsPage.createItem({
			name: 'test-control',
			folder: vars.folderName
		});

		const riskRow = page.getByRole('row', { name: /test-control/i });
		await riskRow.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-owner').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Import a library', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();

		await librariesPage.importLibrary('NIST CSF v2.0', undefined, 'any');

		// Optional: Confirm import
		await librariesPage.tab('Libraries store').click();
		await expect(librariesPage.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();
	});

	await test.step('Create audit', async () => {
		await complianceAssessmentsPage.goto();
		await complianceAssessmentsPage.createItem({
			name: 'test-audit',
			framework: 'NIST CSF',
			perimeter: `${vars.folderName}/${vars.perimeterName}`
		});

		await complianceAssessmentsPage.goto();
		const riskRow = page.getByRole('row', { name: /test-audit/i });
		await riskRow.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-authors').click();
		await page.getByRole('option', { name: 'admin@tests.com' }).click();
		await page.getByTestId('save-button').click();
	});

	await test.step('Verify my assignments contains created entities', async () => {
		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-my-assignments').click();
		await expect(page.locator('#page-title')).toHaveText('My assignments');
		const assignmentsPage = new PageContent(page, '/my-assignments', 'My assignments');
		await assignmentsPage.goto();

		await expect(page).toHaveURL('/my-assignments');

		await expect(page.getByText('test-control')).toBeVisible();
		await expect(page.getByText('test-risk-assessment', { exact: true })).toBeVisible();
		await expect(page.getByText('test-audit')).toBeVisible();
		await expect(page.getByText('test-risk-scenario')).toBeVisible();
		await expect(page.getByText('test-security-exception')).toBeVisible();
	});

	await test.step('Create control without owner and verify absence in my assignments', async () => {
		await appliedControlsPage.goto();
		await appliedControlsPage.createItem({
			name: 'control-without-owner',
			folder: vars.folderName
		});

		await page.getByTestId('accordion-item-overview').click();
		await page.getByTestId('accordion-item-my-assignments').click();
		await expect(page.getByText('control-without-owner')).toHaveCount(0);
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

	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
