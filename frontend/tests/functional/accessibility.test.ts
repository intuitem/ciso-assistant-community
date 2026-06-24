import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '../utils/test-utils.js';
import { writePageReport, type PageReport, type Severity } from '../utils/a11y-report.js';

/**
 * Automated accessibility audit (axe-core) for the key pages of CISO Assistant.
 *
 * Scope note: axe-core fully certifies ~30% of WCAG 2.1 AA success criteria and
 * touches ~62% of the 106 RGAA criteria. It catches roughly half of real-world
 * defects (contrast, labels, name/role/value, lang, headings...). The remaining
 * RGAA criteria (keyboard, screen reader, multimedia, content) still require a
 * manual audit — this spec does NOT certify RGAA conformance.
 *
 * Aggregation: each page writes its own report file (see a11y-report.ts) because
 * Playwright restarts the worker after a failing test, wiping in-memory state.
 * The combined report is built in global teardown.
 */

// WCAG 2.1 levels A + AA, which the automatable RGAA criteria map onto.
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

async function auditPage(page: Page, name: string, path: string): Promise<void> {
	// Let async data tables / charts settle before scanning.
	await page.waitForLoadState('networkidle').catch(() => {});

	const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();

	const report: PageReport = {
		name,
		path,
		violations: results.violations.map((v) => ({
			id: v.id,
			impact: (v.impact as Severity) ?? null,
			help: v.help,
			helpUrl: v.helpUrl,
			wcagTags: v.tags.filter((t) => t.startsWith('wcag')),
			nodes: v.nodes.length,
			sample: v.nodes.slice(0, 3).map((n) => ({
				target: n.target.join(' '),
				html: n.html.slice(0, 200)
			}))
		}))
	};
	writePageReport(report);

	await test.info().attach(`axe-${name}.json`, {
		body: JSON.stringify(results, null, 2),
		contentType: 'application/json'
	});

	const blocking = report.violations.filter(
		(v) => v.impact === 'critical' || v.impact === 'serious'
	);
	const summary = report.violations
		.map((v) => `  [${v.impact}] ${v.id} (${v.nodes}×) — ${v.help}`)
		.join('\n');
	console.log(
		`\n♿ ${name} (${path}): ${report.violations.length} violation type(s), ` +
			`${blocking.length} critical/serious\n${summary}`
	);

	// Surface blocking issues as test failures; lower-impact ones live in the report.
	expect.soft(blocking, `${name} has critical/serious a11y violations`).toEqual([]);
}

// Unauthenticated entry point — the login form is a core RGAA "forms" surface.
test('a11y: login page', async ({ loginPage, page }) => {
	await loginPage.goto();
	await page.locator('body[data-hydrated="true"]').waitFor();
	await auditPage(page, 'login', '/login');
});

// Authenticated key pages: dashboards, representative lists, settings, and
// distinct visual archetypes (calendar grid, x-rays analysis view).
const AUTH_PAGES: { name: string; path: string }[] = [
	{ name: 'analytics-dashboard', path: '/analytics' },
	{ name: 'audits-list', path: '/compliance-assessments' },
	{ name: 'applied-controls-list', path: '/applied-controls' },
	{ name: 'risk-scenarios-list', path: '/risk-scenarios' },
	{ name: 'libraries', path: '/libraries' },
	{ name: 'my-profile-form', path: '/my-profile' },
	{ name: 'settings-form', path: '/settings' },
	{ name: 'calendar', path: '/calendar' },
	{ name: 'x-rays', path: '/x-rays' }
];

for (const { name, path } of AUTH_PAGES) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await page.goto(path);
		await page.locator('body[data-hydrated="true"]').waitFor();
		await auditPage(page, name, path);
	});
}

// Create-form modals — the RGAA "forms" surface (text fields, selects,
// autocompletes, checkboxes) that list/detail pages don't exercise.
const CREATE_FORMS: { name: string; listPath: string }[] = [
	{ name: 'create-applied-control', listPath: '/applied-controls' },
	{ name: 'create-perimeter', listPath: '/perimeters' }
];

for (const { name, listPath } of CREATE_FORMS) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await page.goto(listPath);
		await page.locator('body[data-hydrated="true"]').waitFor();
		await page.getByTestId('add-button').first().click();
		await page.getByTestId('modal-component').waitFor({ state: 'visible' });
		await auditPage(page, name, `${listPath} [create modal]`);
	});
}

// Detail pages and full-page edit forms — reached from the first row of a list.
// Skipped (not failed) when the table is empty, so coverage degrades gracefully.
const ROW_TARGETS: { name: string; listPath: string; action: 'detail' | 'edit' }[] = [
	{ name: 'applied-control-detail', listPath: '/applied-controls', action: 'detail' },
	{ name: 'audit-detail', listPath: '/compliance-assessments', action: 'detail' },
	{ name: 'applied-control-edit', listPath: '/applied-controls', action: 'edit' }
];

for (const { name, listPath, action } of ROW_TARGETS) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await page.goto(listPath);
		await page.locator('body[data-hydrated="true"]').waitFor();
		// Wait for the async table data before counting rows, else we false-skip.
		await page.waitForLoadState('networkidle').catch(() => {});
		const button = page.getByTestId(`tablerow-${action}-button`).first();
		await button.waitFor({ timeout: 5000 }).catch(() => {});
		test.skip((await button.count()) === 0, `no rows in ${listPath} to open`);
		await button.click();
		await page.waitForLoadState('networkidle').catch(() => {});
		await page.locator('body[data-hydrated="true"]').waitFor();
		await auditPage(page, name, `${page.url().replace(/^https?:\/\/[^/]+/, '')} [${action}]`);
	});
}
