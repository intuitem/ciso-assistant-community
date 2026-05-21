/**
 * Companion to visibility-effects.test.ts, exercising the per-role distinction
 * by checking that the "auditor-only" pill ({ auditor: edit, respondent: hidden })
 * actually hides the field from the respondent's view.
 *
 * The auditor-mode tests in visibility-effects.test.ts only cover the
 * everyone/hidden binary. The auditor-only pill is what the visibility system
 * exists for, so it needs respondent-side verification.
 *
 * This test mirrors the TPRM setup (folder → perimeter → library → entity →
 * representative → entity-assessment) because the respondent flow is only
 * reachable through that path.
 */

import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import { SideBar } from '../../utils/sidebar.js';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

const entityAssessment = {
	name: 'Visibility respondent test',
	perimeter: vars.folderName + '/' + vars.perimeterName,
	create_audit: true,
	framework: vars.questionnaire.name,
	representatives: 'third-party@tests.com'
};

test('auditor sets up entity-assessment and hides result from respondent', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	entitiesPage,
	representativesPage,
	entityAssessmentsPage,
	librariesPage,
	complianceAssessmentsPage,
	page
}) => {
	test.slow();

	// Auto-accept any unsaved-changes dialogs (see visibility-effects.test.ts).
	page.on('dialog', (dialog) => dialog.accept());

	// --- Bootstrap -----------------------------------------------------------
	await foldersPage.goto();
	await foldersPage.createItem({ name: vars.folderName, description: vars.description });

	await perimetersPage.goto();
	await perimetersPage.createItem({
		name: vars.perimeterName,
		description: vars.description,
		folder: vars.folderName,
		ref_id: 'R.1234',
		lc_status: 'Production'
	});

	await librariesPage.goto();
	await librariesPage.importLibrary(vars.questionnaire.name, vars.framework.urn);

	await entitiesPage.goto();
	await entitiesPage.createItem(testObjectsData.entitiesPage.build);
	await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);

	await page.getByRole('tab', { name: 'Representatives' }).click();
	await representativesPage.createItem({
		email: 'third-party@tests.com',
		entity: testObjectsData.entitiesPage.build.name,
		create_user: true
	});

	await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);
	await page.getByRole('tab', { name: 'Assessments' }).click();
	await entityAssessmentsPage.createItem(entityAssessment);

	// --- Hide `result` from respondent via auditor-only pill ----------------
	await complianceAssessmentsPage.goto();
	await complianceAssessmentsPage.viewItemDetail(entityAssessment.name);
	await page.getByTestId('edit-button').click();
	await page.getByText('More').click();
	await page.getByTestId('visibility-result-auditor').click();
	await expect(page.getByTestId('visibility-result-auditor')).toHaveAttribute(
		'aria-checked',
		'true'
	);
	await page.getByTestId('save-button').click();
	await page.waitForURL(/\/compliance-assessments\/[^/]+$/);

	// Send the questionnaire so the respondent gets the welcome email.
	await entityAssessmentsPage.goto();
	await entityAssessmentsPage.viewItemDetail(entityAssessment.name);
	await entityAssessmentsPage.isToastVisible(m.mailSuccessfullySent() + /.+/.source);
});

test('respondent sets their password', async ({ mailer, page }) => {
	test.slow();
	await expect(mailer.page.getByText('{{').last()).toBeHidden();
	const welcomeMail = await mailer.getEmailBySubject('Welcome to CISO Assistant!');
	await welcomeMail.open();

	const pagePromise = page.context().waitForEvent('page');
	await mailer.emailContent.setPasswordButton.click();
	const setPasswordPage = await pagePromise;
	await setPasswordPage.waitForLoadState();

	const setLoginPage = new LoginPage(setPasswordPage);
	await setLoginPage.newPasswordInput.fill(vars.thirdPartyUser.password);
	await setLoginPage.confirmPasswordInput.fill(vars.thirdPartyUser.password);
	await setLoginPage.setPasswordButton.click();

	await setLoginPage.login('third-party@tests.com', vars.thirdPartyUser.password);
	await expect(setLoginPage.page).toHaveURL('/auditee-dashboard');

	const passwordPageSideBar = new SideBar(setPasswordPage);
	await passwordPageSideBar.logout();
});

test('respondent does not see result field (auditor-only visibility)', async ({
	thirdPartyAuthenticatedPage,
	page
}) => {
	await expect(page).toHaveURL('/auditee-dashboard');

	await expect(
		page.getByRole('heading', { name: entityAssessment.name, exact: true })
	).toBeVisible();
	await page.getByRole('link', { name: m.startAssessment() }).first().click();
	await page.waitForURL('/auditee-assessments/**');

	// The result field was set to "auditor-only" — it must NOT render in the
	// respondent view, while the rest of the auditee-assessment UI does.
	await expect(page.getByTestId('result-field')).toBeHidden();
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
