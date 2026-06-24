import { playAudit } from 'playwright-lighthouse';
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, type Page } from '../utils/test-utils.js';

/**
 * Lighthouse Accessibility score (0–100) for directly-navigable pages.
 *
 * Lighthouse re-navigates to the URL itself, so pages reached via interaction
 * (modals, row-click detail/edit) can't be measured this way — those are covered
 * by the axe suite instead. The score is recognizable but, per Google, is NOT a
 * conformance measure; it's published as a health indicator alongside the axe
 * results, not as WCAG/RGAA conformance.
 */
const PORT = 9222;
const DIR = join(
	dirname(fileURLToPath(import.meta.url)),
	'..',
	'reports',
	'accessibility',
	'lighthouse'
);

async function lighthouse(page: Page, name: string, path: string): Promise<void> {
	await page.goto(path);
	await page.locator('body[data-hydrated="true"]').waitFor();
	await page.waitForLoadState('networkidle').catch(() => {});

	// Lighthouse audits in its own session, so it loses the Playwright login and
	// every authenticated page redirects to /login. Forward the context cookies as
	// an explicit Cookie header so Lighthouse's requests stay authenticated.
	const cookieHeader = (await page.context().cookies())
		.map((c) => `${c.name}=${c.value}`)
		.join('; ');

	const runAudit = async () =>
		playAudit({
			page,
			port: PORT,
			thresholds: { accessibility: 0 }, // never throws; we record the actual score
			opts: {
				onlyCategories: ['accessibility'],
				disableStorageReset: true,
				// Desktop scope (≥1024px), matching the axe suite — not Lighthouse's mobile default.
				formFactor: 'desktop',
				screenEmulation: { disabled: true },
				extraHeaders: { Cookie: cookieHeader }
			},
			disableLogs: true
		});

	const redirected = (lhr: any) =>
		path !== '/login' && String(lhr.finalDisplayedUrl ?? lhr.finalUrl).includes('/login');

	// Lighthouse occasionally loses the session and lands on /login; retry once so
	// we never record a login-page score under an authenticated page's name.
	let { lhr } = await runAudit();
	if (redirected(lhr)) ({ lhr } = await runAudit());

	const finalUrl = String(lhr.finalDisplayedUrl ?? lhr.finalUrl);
	const score = Math.round((lhr.categories.accessibility.score ?? 0) * 100);
	const failed = (lhr.categories.accessibility.auditRefs ?? [])
		.map((ref) => lhr.audits[ref.id])
		.filter((a) => a && a.score === 0)
		.map((a) => a.id);
	if (!existsSync(DIR)) mkdirSync(DIR, { recursive: true });
	writeFileSync(
		join(DIR, `${name}.json`),
		JSON.stringify({ name, path, score, finalUrl, failed }, null, 2)
	);
	console.log(
		`🔦 ${name} (${path}): ${score}/100  finalUrl=${finalUrl}  failed=[${failed.join(', ')}]`
	);
}

test.beforeAll(() => rmSync(DIR, { recursive: true, force: true }));

test('lighthouse: login', async ({ loginPage, page }) => {
	await loginPage.goto();
	await page.locator('body[data-hydrated="true"]').waitFor();
	await lighthouse(page, 'login', '/login');
});

const PAGES: [string, string][] = [
	['analytics-dashboard', '/analytics'],
	['applied-controls-list', '/applied-controls'],
	['my-profile-form', '/my-profile'],
	['libraries', '/libraries'],
	['reports', '/reports']
];

for (const [name, path] of PAGES) {
	test(`lighthouse: ${name}`, async ({ logedPage, page }) => {
		await lighthouse(page, name, path);
	});
}
