import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('CA visibility editor: pill selection round-trips through save/reload', async ({
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

	// Default state assertions.
	// score defaults to HIDDEN → the "hidden" pill is checked.
	await expect(page.getByTestId('visibility-score-hidden')).toHaveAttribute('aria-checked', 'true');
	// status defaults to AUDITOR_ONLY.
	await expect(page.getByTestId('visibility-status-auditor')).toHaveAttribute(
		'aria-checked',
		'true'
	);
	// observation has no DEFAULT_VISIBILITY entry → resolves to "everyone".
	await expect(page.getByTestId('visibility-observation-everyone')).toHaveAttribute(
		'aria-checked',
		'true'
	);

	// Cascade: while score is hidden, documentation_score's non-hidden pills are disabled.
	await expect(page.getByTestId('visibility-documentation_score-everyone')).toBeDisabled();
	await expect(page.getByTestId('visibility-documentation_score-auditor')).toBeDisabled();
	await expect(page.getByTestId('visibility-documentation_score-hidden')).toBeEnabled();

	// Mutate: turn score visible to A+R.
	await page.getByTestId('visibility-score-everyone').click();
	await expect(page.getByTestId('visibility-score-everyone')).toHaveAttribute(
		'aria-checked',
		'true'
	);
	// Now doc_score's other options unlock.
	await expect(page.getByTestId('visibility-documentation_score-auditor')).toBeEnabled();

	// Restrict status to Hidden.
	await page.getByTestId('visibility-status-hidden').click();
	await expect(page.getByTestId('visibility-status-hidden')).toHaveAttribute(
		'aria-checked',
		'true'
	);

	// Save and wait for the navigation back to the detail page.
	await page.getByTestId('save-button').click();
	await page.waitForURL(/\/compliance-assessments\/[^/]+$/);

	// Reopen the edit form and assert the chosen pills are still highlighted —
	// proving the per-role pair was persisted and read back correctly.
	await page.getByTestId('edit-button').click();
	await page.getByText('More').click();
	await expect(page.getByTestId('visibility-score-everyone')).toHaveAttribute(
		'aria-checked',
		'true'
	);
	await expect(page.getByTestId('visibility-status-hidden')).toHaveAttribute(
		'aria-checked',
		'true'
	);
	// status=hidden doesn't constrain anything, but score=everyone preserves
	// the doc_score row's freedom.
	await expect(page.getByTestId('visibility-documentation_score-auditor')).toBeEnabled();
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
