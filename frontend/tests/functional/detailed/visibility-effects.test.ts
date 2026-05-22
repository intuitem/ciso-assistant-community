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
 *   - visibility-effects-respondent.test.ts covers the auditor-only pill
 *     from the respondent's view (this file only exercises the auditor).
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

test('field visibility effects: each flag toggles the corresponding UI', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	// The matrix walks ~16 visibility cycles; the default 100s timeout is tight.
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

	// Resolve the URL of an assessable requirement assessment edit page ONCE
	// via tree traversal, then reuse direct navigation in every subsequent
	// step. Repeated tree traversals were flaky after multiple visibility
	// edits (apparent localStorage/state interaction in the tree widget).
	// NIST CSF v1.1 has ID.AM-1 (Identify → Asset Management) — use it.
	const IDAM1 = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-1', [
		'ID - Identify',
		'ID.AM - Asset Management'
	]);
	await IDAM1.content.click();
	await page.waitForURL('/requirement-assessments/**');
	// The tree click navigates straight to /edit for users with edit perms
	// (admin in tests). Drop the ?next=... so we can reuse the bare URL.
	const raEditUrl = page.url().split('?')[0];

	/**
	 * Set one or more field visibilities and persist. Always starts from the
	 * audit detail page and ends there too, so callers don't need to track
	 * page state between iterations.
	 */
	async function setVisibility(...pairs: Array<[string, Pill]>) {
		await page.goto(auditDetailUrl);
		await page.getByTestId('edit-button').click();
		await page.getByText('More').click();
		for (const [field, pill] of pairs) {
			await page.getByTestId(`visibility-${field}-${pill}`).click();
			await expect(page.getByTestId(`visibility-${field}-${pill}`)).toHaveAttribute(
				'aria-checked',
				'true'
			);
		}
		await page.getByTestId('save-button').click();
		await page.waitForURL(/\/compliance-assessments\/[^/]+$/);
	}

	// === Matrix: each field hidden then visible ============================
	// Fields that render in the audit overview (donut charts, etc.) AND in
	// the RA edit form. We check both surfaces.
	type FieldCheck = {
		field: string;
		// Asserts the field is rendered (or not) in its UI locations.
		assertOverview?: (visible: boolean) => Promise<void>;
		assertRaEdit?: (visible: boolean) => Promise<void>;
		// Some fields require setting a parent first (e.g. doc_score needs score).
		dependsOn?: Array<[string, Pill]>;
	};

	// answers is not in the matrix because NIST CSF v1.1 has no per-requirement
	// questions, so the answers-field testid never renders regardless of pill.
	const checks: FieldCheck[] = [
		{
			field: 'result',
			assertOverview: async (visible) => {
				await expect(page.locator('#compliance_result_div')).toHaveCount(visible ? 1 : 0);
			},
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('result-field')).toBeVisible();
				else await expect(page.getByTestId('result-field')).toBeHidden();
			}
		},
		{
			field: 'status',
			assertOverview: async (visible) => {
				await expect(page.locator('#compliance_status_div')).toHaveCount(visible ? 1 : 0);
			},
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('status-field')).toBeVisible();
				else await expect(page.getByTestId('status-field')).toBeHidden();
			}
		},
		{
			field: 'score',
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('score-field')).toBeVisible();
				else await expect(page.getByTestId('score-field')).toBeHidden();
			}
		},
		{
			field: 'documentation_score',
			// doc_score visibility cannot exceed score's — keep score visible.
			dependsOn: [['score', 'everyone']],
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('documentation-score-field')).toBeVisible();
				else await expect(page.getByTestId('documentation-score-field')).toBeHidden();
			}
		},
		{
			field: 'extended_result',
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('extended-result-field')).toBeVisible();
				else await expect(page.getByTestId('extended-result-field')).toBeHidden();
			}
		},
		{
			field: 'observation',
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('observation-field')).toBeVisible();
				else await expect(page.getByTestId('observation-field')).toBeHidden();
			}
		},
		{
			field: 'applied_controls',
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('applied-controls-tab')).toBeVisible();
				else await expect(page.getByTestId('applied-controls-tab')).toBeHidden();
			}
		},
		{
			field: 'evidences',
			assertRaEdit: async (visible) => {
				if (visible) await expect(page.getByTestId('evidences-tab')).toBeVisible();
				else await expect(page.getByTestId('evidences-tab')).toBeHidden();
			}
		}
	];

	for (const check of checks) {
		for (const pill of ['hidden', 'everyone'] as Pill[]) {
			const visible = pill === 'everyone';
			const settings: Array<[string, Pill]> = [...(check.dependsOn ?? []), [check.field, pill]];
			await setVisibility(...settings);
			// After setVisibility we're on auditDetailUrl. Audit-overview assertions
			// must run before navigating away.
			if (check.assertOverview) await check.assertOverview(visible);
			if (check.assertRaEdit) {
				await page.goto(raEditUrl);
				await check.assertRaEdit(visible);
			}
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
