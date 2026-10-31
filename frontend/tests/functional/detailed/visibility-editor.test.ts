import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '#paraglide/messages.js';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('CA visibility editor: per-role access round-trips through save/reload', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	// Bootstrap: folder + perimeter + CA.
	for (const requirement of ['folders', 'perimeters', 'complianceAssessments']) {
		const requiredPage = pages[requirement + 'Page'];
		await requiredPage.goto();
		await requiredPage.hasUrl();
		await requiredPage.createItem(
			testObjectsData[requirement + 'Page'].build,
			'dependency' in testObjectsData[requirement + 'Page']
				? testObjectsData[requirement + 'Page'].dependency
				: null
		);
		await requiredPage.goto();
		await requiredPage.hasUrl();
	}

	await complianceAssessmentsPage.viewItemDetail(
		testObjectsData.complianceAssessmentsPage.build.name
	);

	// Open edit form, expand the More dropdown to reveal the visibility editor.
	await page.getByTestId('edit-button').click();
	await page.getByText('More').click();

	// Each field has one radio group per role: visibility-<field>-<role>-<access>.
	const option = (field: string, role: 'auditor' | 'respondent', access: string) =>
		page.getByTestId(`visibility-${field}-${role}-${access}`);
	const expectChecked = (field: string, role: 'auditor' | 'respondent', access: string) =>
		expect(option(field, role, access)).toHaveAttribute('aria-checked', 'true');

	// Default state assertions.
	// score defaults to HIDDEN for both roles.
	await expectChecked('score', 'auditor', 'hidden');
	await expectChecked('score', 'respondent', 'hidden');
	// status defaults to AUDITOR_ONLY.
	await expectChecked('status', 'auditor', 'edit');
	await expectChecked('status', 'respondent', 'hidden');
	// observation has no DEFAULT_VISIBILITY entry → resolves to edit for both roles.
	await expectChecked('observation', 'auditor', 'edit');
	await expectChecked('observation', 'respondent', 'edit');

	// Cascade: while score is hidden, documentation_score cannot be opened up.
	await expect(option('documentation_score', 'auditor', 'edit')).toBeDisabled();
	await expect(option('documentation_score', 'auditor', 'read')).toBeDisabled();
	await expect(option('documentation_score', 'auditor', 'hidden')).toBeEnabled();
	// The respondent never sees more than the auditor.
	await expect(option('score', 'respondent', 'edit')).toBeDisabled();

	// Mutate: open score to the auditor, then to the respondent.
	await option('score', 'auditor', 'edit').click();
	await expectChecked('score', 'auditor', 'edit');
	await expectChecked('score', 'respondent', 'hidden');
	await option('score', 'respondent', 'edit').click();
	await expectChecked('score', 'respondent', 'edit');
	// Now doc_score's other options unlock.
	await expect(option('documentation_score', 'auditor', 'edit')).toBeEnabled();

	// Hide status from the auditor: the respondent is dragged down with it.
	await option('status', 'auditor', 'hidden').click();
	await expectChecked('status', 'auditor', 'hidden');
	await expectChecked('status', 'respondent', 'hidden');

	// Save and wait for the navigation back to the detail page.
	await page.getByTestId('save-button').click();
	await page.waitForURL(/\/compliance-assessments\/[^/]+$/);

	// Reopen the edit form and assert the chosen access is still selected —
	// proving the per-role pair was persisted and read back correctly.
	await page.getByTestId('edit-button').click();
	await page.getByText('More').click();
	await expectChecked('score', 'auditor', 'edit');
	await expectChecked('score', 'respondent', 'edit');
	await expectChecked('status', 'auditor', 'hidden');
	await expectChecked('status', 'respondent', 'hidden');
	await expect(option('documentation_score', 'auditor', 'edit')).toBeEnabled();
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
