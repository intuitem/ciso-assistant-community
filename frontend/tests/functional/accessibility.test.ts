import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '../utils/test-utils.js';
import { writePageReport, type PageReport, type Severity } from '../utils/a11y-report.js';

// axe-core audit of CISO Assistant's key pages. Each page writes its own report
// file (a11y-report.ts) because Playwright restarts the worker on a failing test;
// the combined report is built in global teardown.

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

// Desktop-scoped; not the WCAG 1.4.10 320px target — see the accessibility statement.
const REFLOW_MIN_WIDTH = 1024;

const THEME: 'light' | 'dark' = process.env.A11Y_THEME === 'dark' ? 'dark' : 'light';
const suffix = THEME === 'dark' ? '-dark' : '';

// The app derives `.dark` on <html> from localStorage 'ciso-theme'.
async function applyThemePref(page: Page): Promise<void> {
	if (THEME !== 'dark') return;
	await page.emulateMedia({ colorScheme: 'dark' });
	await page.addInitScript(() => {
		try {
			localStorage.setItem('ciso-theme', 'dark');
		} catch {
			/* storage unavailable pre-navigation */
		}
	});
}

async function auditPage(page: Page, name: string, path: string): Promise<void> {
	await page.waitForLoadState('networkidle').catch(() => {});

	const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
	if (THEME === 'dark') {
		expect.soft(isDark, `${name}: dark theme did not apply`).toBe(true);
	}

	const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();

	await page.setViewportSize({ width: REFLOW_MIN_WIDTH, height: 900 });
	const horizontalOverflowPx = await page.evaluate(() =>
		Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)
	);

	const report: PageReport = {
		name: `${name}${suffix}`,
		path,
		theme: THEME,
		passes: results.passes.length,
		incomplete: results.incomplete.length,
		reflow: { horizontalOverflowPx },
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

	expect.soft(blocking, `${name} has critical/serious a11y violations`).toEqual([]);
}

test('a11y: login page', async ({ loginPage, page }) => {
	await applyThemePref(page);
	await loginPage.goto();
	await page.locator('body[data-hydrated="true"]').waitFor();
	await auditPage(page, 'login', '/login');
});

const AUTH_PAGES: { name: string; path: string }[] = [
	{ name: 'analytics-dashboard', path: '/analytics' },
	{ name: 'audits-list', path: '/compliance-assessments' },
	{ name: 'applied-controls-list', path: '/applied-controls' },
	{ name: 'risk-scenarios-list', path: '/risk-scenarios' },
	{ name: 'libraries', path: '/libraries' },
	{ name: 'my-profile-form', path: '/my-profile' },
	{ name: 'settings-form', path: '/settings' },
	{ name: 'calendar', path: '/calendar' },
	{ name: 'x-rays', path: '/x-rays' },
	{ name: 'entities-graph', path: '/entities/graph' },
	{ name: 'reports', path: '/reports' }
];

for (const { name, path } of AUTH_PAGES) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await applyThemePref(page);
		await page.goto(path);
		await page.locator('body[data-hydrated="true"]').waitFor();
		await auditPage(page, name, path);
	});
}

// Create-form modals — exercise the form widgets lists/details don't.
const CREATE_FORMS: { name: string; listPath: string }[] = [
	{ name: 'create-applied-control', listPath: '/applied-controls' },
	{ name: 'create-perimeter', listPath: '/perimeters' },
	{ name: 'upload-library-modal', listPath: '/libraries' }
];

for (const { name, listPath } of CREATE_FORMS) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await applyThemePref(page);
		await page.goto(listPath);
		await page.locator('body[data-hydrated="true"]').waitFor();
		await page.getByTestId('add-button').first().click();
		await page.getByTestId('modal-component').waitFor({ state: 'visible' });
		await auditPage(page, name, `${listPath} [create modal]`);
	});
}

// Detail / edit pages reached from the first row; skipped when the table is empty.
const ROW_TARGETS: { name: string; listPath: string; action: 'detail' | 'edit' }[] = [
	{ name: 'applied-control-detail', listPath: '/applied-controls', action: 'detail' },
	{ name: 'audit-detail', listPath: '/compliance-assessments', action: 'detail' },
	{ name: 'applied-control-edit', listPath: '/applied-controls', action: 'edit' },
	{ name: 'risk-matrix-detail', listPath: '/risk-matrices', action: 'detail' },
	{ name: 'risk-assessment-detail', listPath: '/risk-assessments', action: 'detail' }
];

for (const { name, listPath, action } of ROW_TARGETS) {
	test(`a11y: ${name}`, async ({ logedPage, page }) => {
		await applyThemePref(page);
		await page.goto(listPath);
		await page.locator('body[data-hydrated="true"]').waitFor();
		// Wait for table data before counting rows, else we false-skip.
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
