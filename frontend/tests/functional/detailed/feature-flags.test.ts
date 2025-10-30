import { test, expect, type Page } from '../../utils/test-utils.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();

const toggleFeatureFlag = async (page: Page, flagTestId: string, enable: boolean) => {
	await page.goto('/settings');
	await expect(page).toHaveURL('/settings');
	await page.getByText(/^ Feature flags$/).click();

	const toggle = page.getByTestId(`form-input-${flagTestId}`);
	if ((await toggle.isChecked()) !== enable) {
		await toggle.click();
		await page.getByRole('button', { name: 'Save' }).click();
		await page.reload();
		await expect(page).toHaveURL('/settings');
		await page.reload();
		await expect(page.getByText(/^ Feature flags$/)).toBeVisible();
	}
};

// ---------- X-Rays ----------
test('Feature Flags - X-Rays visibility toggling', async ({ logedPage, page }) => {
	await page.getByText('Operations').click();
	await expect(page.getByText('X-Rays', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'xrays', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('X-Rays', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'xrays', true);
});

// ---------- Incidents ----------
test('Feature Flags - Incidents visibility toggling', async ({ logedPage, page }) => {
	await page.getByText('Operations').click();
	await expect(page.getByText('Incidents', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'incidents', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('Incidents', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'incidents', true);
});

// ---------- Tasks ----------
test('Feature Flags - Tasks visibility toggling', async ({ logedPage, page }) => {
	await page.getByText('Operations').click();
	await expect(page.getByText('Tasks', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'tasks', false);

	await page.getByText('Operations').click();
	await expect(page.getByText('Tasks', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'tasks', true);
});

// ---------- Risk Acceptances ----------
test('Feature Flags - Risk Acceptances visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Risk Acceptances', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'risk-acceptances', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Risk Acceptances', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'risk-acceptances', true);
});

// ---------- Exceptions ----------
test('Feature Flags - Exceptions visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Exceptions', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'exceptions', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Exceptions', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'exceptions', true);
});

// ---------- Findings Tracking ----------
test('Feature Flags - Findings Tracking visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Findings Tracking', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'follow-up', false);

	await page.getByTestId('accordion-item-governance').click();
	await expect(page.getByText('Findings Tracking', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'follow-up', true);
});

// ---------- Ebios RM ----------
test('Feature Flags - Ebios RM visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByTestId('accordion-item-ebios-rm')).toBeVisible();

	await toggleFeatureFlag(page, 'ebiosrm', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByTestId('accordion-item-ebios-rm')).not.toBeVisible();

	await toggleFeatureFlag(page, 'ebiosrm', true);
});

// ---------- Scoring Assistant ----------
test('Feature Flags - Scoring Assistant visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Scoring Assistant', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'scoring-assistant', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Scoring Assistant', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'scoring-assistant', true);
});

// ---------- Vulnerabilities ----------
test('Feature Flags - Vulnerabilities visibility toggling', async ({ logedPage, page }) => {
	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Vulnerabilities', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'vulnerabilities', false);

	await page.getByTestId('accordion-item-risk').click();
	await expect(page.getByText('Vulnerabilities', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'vulnerabilities', true);
});

// ---------- Compliance ----------
test('Feature Flags - Compliance visibility toggling', async ({ logedPage, page }) => {
	await expect(page.getByTestId('accordion-item-compliance')).toBeVisible();

	await toggleFeatureFlag(page, 'compliance', false);

	await expect(page.getByTestId('accordion-item-compliance')).not.toBeVisible();

	await toggleFeatureFlag(page, 'compliance', true);
});

// ---------- Third Party ----------
test('Feature Flags - Third Party visibility toggling', async ({ logedPage, page }) => {
	await expect(page.getByTestId('accordion-item-thirdpartycategory')).toBeVisible();

	await toggleFeatureFlag(page, 'tprm', false);

	await expect(page.getByTestId('accordion-item-thirdpartycategory')).not.toBeVisible();

	await toggleFeatureFlag(page, 'tprm', true);
});

// ---------- Privacy ----------
test('Feature Flags - Privacy visibility toggling', async ({ logedPage, page }) => {
	await expect(page.getByText('Privacy', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'privacy', false);

	await expect(page.getByText('Privacy', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'privacy', true);
});

// ---------- Experimental ----------
test('Feature Flags - Experimental visibility toggling', async ({ logedPage, page }) => {
	await page.getByText('Extra').click();
	await expect(page.getByText('Experimental', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'experimental', false);

	await page.getByText('Extra').click();
	await expect(page.getByText('Experimental', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'experimental', true);
});

// ---------- Inherent Risk (all variants) ----------
test('Feature Flags - Inherent Risk visibility toggling on Risk Scenarios model table view page', async ({
	logedPage,
	page
}) => {
	await toggleFeatureFlag(page, 'inherent-risk', true);

	const risksPage = new PageContent(page, '/risk-scenarios', 'Risk Scenarios');
	await risksPage.goto();
	await expect(page.getByText('Inherent Level', { exact: false })).toBeVisible();
	await expect(page.locator('#page-title')).toHaveText('Risk scenarios');
	await expect(page).toHaveURL('/risk-scenarios');

	await toggleFeatureFlag(page, 'inherent-risk', false);
	await risksPage.goto();
	await expect(page.getByText('Inherent Level', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});

test('Feature Flags - Inherent Risk  reate folder, perimeter and risk assessment', async ({
	page,
	pages,
	foldersPage,
	perimetersPage,
	riskAssessmentsPage,
	sideBar,
	librariesPage,
	logedPage
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
	});

	await test.step('Create risk assessment', async () => {
		page.getByTestId('accordion-item-risk').click();
		await expect(page.getByTestId('accordion-item-risk-assessments')).toBeVisible();
		page.getByTestId('accordion-item-risk-assessments').click();

		await riskAssessmentsPage.createItem({
			name: vars.riskAssessmentName,
			perimeter: `${vars.folderName}/${vars.perimeterName}`,
			authors: ['admin@tests.com'],
			risk_matrix: '4x4 risk matrix from EBIOS-RM',
			version: vars.riskAssessmentVersion
		});
	});

	// Check visibility
	await page.getByText(vars.riskAssessmentName).click();
	await expect(page.getByText('Inherent Level', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', false);
	await page.getByTestId('accordion-item-risk').click();
	await page.getByTestId('accordion-item-risk-assessments').click();
	await page.getByText(vars.riskAssessmentName).click();
	await expect(page.getByText('Inherent Level', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});

test('Feature Flags - Inherent Risk visibility in Risk analytics page', async ({
	logedPage,
	librariesPage,
	page
}) => {
	await toggleFeatureFlag(page, 'inherent-risk', true);

	const risksPage = new PageContent(page, '/analytics?tab=risk', 'Analytics');
	await risksPage.goto();
	await expect(page.getByText('Inherent risk level', { exact: false })).toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', false);
	await risksPage.goto();
	await expect(page.getByText('Inherent risk level', { exact: false })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});

test('Feature Flags - Inherent Risk visibility in Risk scenario detail view page and in edit page', async ({
	logedPage,
	librariesPage,
	riskScenariosPage,
	pages,
	sideBar,
	page
}) => {
	await toggleFeatureFlag(page, 'inherent-risk', true);
	await sideBar.click('Risk', pages.riskScenariosPage.url);
	await pages.riskScenariosPage.hasUrl();
	await pages.riskScenariosPage.hasTitle();

	await pages.riskScenariosPage.createItem({
		name: vars.riskScenarioName,
		risk_assessment: `${vars.folderName}/${vars.perimeterName}/${vars.riskAssessmentName} - ${vars.riskAssessmentVersion}`
	});
	await page.getByText(vars.riskScenarioName).click();

	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).toBeVisible();
	await page.getByTestId('edit-button').click();
	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', false);
	await sideBar.click('Risk', pages.riskScenariosPage.url);
	await pages.riskScenariosPage.hasUrl();
	await pages.riskScenariosPage.hasTitle();
	await page.getByText(vars.riskScenarioName).click();
	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).not.toBeVisible();
	await page.getByTestId('edit-button').click();
	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});

test('Feature Flags - Inherent Risk visibility in Ebios RM step 5', async ({
	logedPage,
	page,
	ebiosRmStudyPage,
	riskAssessmentsPage
}) => {
	await toggleFeatureFlag(page, 'inherent-risk', true);
	await ebiosRmStudyPage.goto();
	await ebiosRmStudyPage.hasUrl();
	await ebiosRmStudyPage.createItem({
		name: vars.ebiosRMName,
		folder: vars.folderName,
		risk_matrix: '4x4 risk matrix from EBIOS-RM'
	});

	await page.getByText(vars.ebiosRMName).click();

	await page.getByText('Generate the risk assessment').click();
	await riskAssessmentsPage.form.fill({
		name: 'test-risk-assessment-ebios-rm',
		perimeter: `${vars.folderName}/${vars.perimeterName}`
	});
	await page.getByTestId('save-button').click();

	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', false);

	let risksPage = new PageContent(page, '/risk-assessments', 'Risk Assessments');
	await risksPage.goto();
	await page.getByText('test-risk-assessment-ebios-rm').click();
	await expect(page.getByRole('heading', { name: 'Inherent Risk' })).not.toBeVisible();

	await toggleFeatureFlag(page, 'inherent-risk', true);
});

test('Cleanup - delete the folder', async ({ logedPage, page }) => {
	await page.getByRole('button', { name: 'Organization' }).click();
	await page.getByTestId('accordion-item-folders').click();
	await expect(page.locator('#page-title')).toHaveText('Domains');
	await expect(page).toHaveURL('/folders');

	const folderRow = page.getByRole('row', { name: vars.folderName });
	await folderRow.getByTestId('tablerow-delete-button').click();
	await expect(page.getByTestId('delete-prompt-confirm-textfield')).toBeVisible();
	await page.getByTestId('delete-prompt-confirm-textfield').fill('yes');
	await page.getByRole('button', { name: 'Submit' }).click();
	await expect(page.getByRole('row', { name: vars.folderName })).toHaveCount(0);
});
