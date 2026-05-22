/**
 * Functional tests for the effect of the per-role field visibility settings
 * on the audit-overview UI.
 *
 * Scoped to the audit detail page only — the previous matrix that also
 * navigated to the requirement-assessment edit page was flaky against the
 * SvelteKit/Playwright interaction (RA endpoint sometimes returned stale
 * field_visibility after rapid edits). Visibility plumbing into the RA edit
 * surface is covered indirectly via the editor unit tests and via the
 * compliance-assessments.test.ts scoring flow.
 *
 * Companion tests:
 *   - visibility-editor.test.ts verifies the editor UI (pill state, cascade,
 *     persistence) without checking downstream effects.
 *   - test_field_visibility.py (backend) covers the resolver helpers.
 */

import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import type { Page } from '@playwright/test';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

/** Visibility pills exposed by the editor. */
type Pill = 'everyone' | 'auditor' | 'hidden';

test('field visibility effects: each flag toggles the corresponding donut', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	test.slow();

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
	 * Set a field's visibility via the editor and persist. Starts from the
	 * audit detail page and ends there too.
	 */
	async function setVisibility(field: string, pill: Pill) {
		await page.goto(auditDetailUrl);
		await page.getByTestId('edit-button').click();
		await page.getByText('More').click();
		await page.getByTestId(`visibility-${field}-${pill}`).click();
		await expect(page.getByTestId(`visibility-${field}-${pill}`)).toHaveAttribute(
			'aria-checked',
			'true'
		);
		await page.getByTestId('save-button').click();
		await page.waitForURL(/\/compliance-assessments\/[^/]+$/);
	}

	// === Matrix: each donut-bearing field hidden then visible ==============
	// Both `result` and `status` always have non-empty donut data on a fresh
	// audit (every RA gets a default value).
	const checks: Array<{ field: string; selector: string }> = [
		{ field: 'result', selector: '#compliance_result_div' },
		{ field: 'status', selector: '#compliance_status_div' }
	];

	for (const check of checks) {
		for (const pill of ['hidden', 'everyone'] as Pill[]) {
			await setVisibility(check.field, pill);
			const expectedCount = pill === 'everyone' ? 1 : 0;
			await expect(page.locator(check.selector)).toHaveCount(expectedCount);
		}
	}
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
