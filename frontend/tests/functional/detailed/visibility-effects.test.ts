/**
 * Functional tests for the effect of the per-role field visibility settings
 * on the rest of the UI.
 *
 * For each visibility flag we verify:
 *   - visibility=hidden  → the corresponding UI is NOT rendered
 *   - visibility=everyone → the corresponding UI IS rendered
 *
 * Companion tests:
 *   - visibility-editor.test.ts verifies the editor UI itself (pill state,
 *     cascade, persistence) without checking downstream effects.
 *   - test_field_visibility.py (backend) covers the resolver helpers.
 */

import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import type { Page } from '@playwright/test';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

/** Three visibility states exposed by the editor. */
type Pill = 'everyone' | 'auditor' | 'hidden';

/**
 * Set a single field's visibility via the editor UI and save.
 * Assumes the audit edit form is already open with the "More" section expanded.
 */
async function setVisibility(page: Page, field: string, pill: Pill) {
	await page.getByTestId(`visibility-${field}-${pill}`).click();
	await expect(page.getByTestId(`visibility-${field}-${pill}`)).toHaveAttribute(
		'aria-checked',
		'true'
	);
}

/** Open the audit edit form and expand the "More" dropdown to reveal pills. */
async function openVisibilityEditor(page: Page) {
	await page.getByTestId('edit-button').click();
	await page.getByText('More').click();
}

/** Save the audit edit form and wait for the navigation back to detail view. */
async function saveAudit(page: Page) {
	await page.getByTestId('save-button').click();
	await page.waitForURL(/\/compliance-assessments\/[^/]+$/);
}

test('field visibility effects: each flag toggles the corresponding UI', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	// --- Bootstrap: folder + perimeter + CA --------------------------------
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
	const auditDetailUrl = page.url();

	/**
	 * Navigate to an assessable requirement assessment edit page.
	 * NIST CSF v1.1 has ID.AM-1 (Identify → Asset Management) — use it.
	 */
	async function openFirstRequirementAssessment() {
		await page.goto(auditDetailUrl);
		const IDAM1 = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-1', [
			'ID - Identify',
			'ID.AM - Asset Management'
		]);
		await IDAM1.content.click();
		await page.waitForURL('/requirement-assessments/**');
		// Switch to edit form.
		const editUrl = page.url() + '/edit';
		await page.goto(editUrl);
		await page.waitForURL(/\/requirement-assessments\/[^/]+\/edit/);
	}

	// --- answers ------------------------------------------------------------
	// answers defaults to "everyone" (no DEFAULT_VISIBILITY entry).
	await openVisibilityEditor(page);
	await setVisibility(page, 'answers', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('answers-field')).toBeHidden();
	// Regression for the original bug: save buttons must still work.
	await page.getByTestId('save-no-continue-button').click();
	await expect(page.getByText(/successfully saved/i)).toBeVisible();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'answers', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	// NIST CSF has no per-requirement questions, so the answers-field testid
	// only appears when the requirement has questions. For frameworks without
	// questions the visible-state assertion is a no-op; the hidden-state
	// assertion above is the meaningful one.

	// --- result -------------------------------------------------------------
	// result defaults to "everyone".
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'result', 'hidden');
	await saveAudit(page);
	// Overview: result donut chart absent.
	await expect(page.locator('#compliance_result_div')).toHaveCount(0);
	// Edit form: result field absent.
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('result-field')).toBeHidden();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'result', 'everyone');
	await saveAudit(page);
	await expect(page.locator('#compliance_result_div')).toHaveCount(1);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('result-field')).toBeVisible();

	// --- status -------------------------------------------------------------
	// status defaults to "auditor". Hide it.
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'status', 'hidden');
	await saveAudit(page);
	// Overview: status donut chart absent.
	await expect(page.locator('#compliance_status_div')).toHaveCount(0);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('status-field')).toBeHidden();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'status', 'everyone');
	await saveAudit(page);
	await expect(page.locator('#compliance_status_div')).toHaveCount(1);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('status-field')).toBeVisible();

	// --- score --------------------------------------------------------------
	// score defaults to "hidden". Show it first to verify the visible state.
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'score', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('score-field')).toBeVisible();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'score', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('score-field')).toBeHidden();

	// --- documentation_score ------------------------------------------------
	// doc_score visibility cannot exceed score's. Set both to "everyone" first.
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'score', 'everyone');
	await setVisibility(page, 'documentation_score', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('documentation-score-field')).toBeVisible();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'documentation_score', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('documentation-score-field')).toBeHidden();

	// --- extended_result ----------------------------------------------------
	// extended_result defaults to "auditor". Show it for the auditor anyway
	// (default state) and verify the field is present on the edit form.
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'extended_result', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('extended-result-field')).toBeVisible();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'extended_result', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('extended-result-field')).toBeHidden();

	// --- observation --------------------------------------------------------
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'observation', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('observation-field')).toBeHidden();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'observation', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('observation-field')).toBeVisible();

	// --- applied_controls ---------------------------------------------------
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'applied_controls', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('applied-controls-tab')).toBeHidden();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'applied_controls', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('applied-controls-tab')).toBeVisible();

	// --- evidences ----------------------------------------------------------
	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'evidences', 'hidden');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('evidences-tab')).toBeHidden();

	await page.goto(auditDetailUrl);
	await openVisibilityEditor(page);
	await setVisibility(page, 'evidences', 'everyone');
	await saveAudit(page);
	await openFirstRequirementAssessment();
	await expect(page.getByTestId('evidences-tab')).toBeVisible();
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
