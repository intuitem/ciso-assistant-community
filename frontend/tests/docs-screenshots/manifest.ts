import type { Locator, Page } from '@playwright/test';

export interface Shot {
	/** Output file name, without extension. Becomes `.gitbook/assets/<slug>.png`. */
	slug: string;
	/** Route to open, relative to the app root. */
	url: string;
	/** Which doc pages consume this image — kept here so a stale shot is traceable. */
	usedBy: string[];
	/** Capture the whole scrollable page instead of the viewport. */
	fullPage?: boolean;
	/** Restrict the capture to one element — usually what a doc actually needs. */
	clip?: (page: Page) => Locator;
	/** Extra interaction to run once the route has settled. */
	then?: (page: Page) => Promise<void>;
}

/**
 * Row names in ModelTable are plain text, not links — the only anchor to the
 * detail page is the row's view action. Match the row by its ref_id (stable,
 * seeded) and follow that row's own detail anchor; taking the first anchor on
 * the page silently lands on whichever row happens to sort first.
 */
function openDetail(model: string, refId: string) {
	return async (page: Page) => {
		const row = page.locator('tr', { hasText: refId }).first();
		const href = await row.locator(`a[href^="/${model}/"]`).first().getAttribute('href');
		if (!href || !/[0-9a-f-]{36}/.test(href)) {
			throw new Error(`no detail link on the /${model} row for ${refId} (got ${href})`);
		}
		await page.goto(href);
		await page.locator('body[data-hydrated="true"]').waitFor();
	};
}

export const shots: Shot[] = [
	{
		slug: 'analytics-overview',
		url: '/analytics',
		usedBy: ['concepts/metrics.md', 'guides/general-tips.md']
	},
	{
		slug: 'domains-list',
		url: '/folders',
		usedBy: ['concepts/domains.md', 'guides/initial-setup.md']
	},
	{
		slug: 'perimeters-list',
		url: '/perimeters',
		usedBy: ['concepts/perimeters.md', 'guides/first-perimeter.md']
	},
	{
		slug: 'assets-list',
		url: '/assets',
		usedBy: ['concepts/assets.md']
	},
	{
		slug: 'applied-controls-list',
		url: '/applied-controls',
		usedBy: ['concepts/applied-controls.md']
	},
	{
		slug: 'audits-list',
		url: '/compliance-assessments',
		usedBy: ['concepts/audits.md', 'guides/first-audit.md']
	},
	{
		slug: 'audit-detail',
		url: '/compliance-assessments',
		usedBy: ['concepts/audits.md', 'guides/basic-audit.md'],
		then: openDetail('compliance-assessments', 'AUD.2026.01')
	},
	{
		slug: 'risk-assessment-detail',
		url: '/risk-assessments',
		usedBy: ['concepts/risk-assessments.md', 'guides/first-risk-assessment.md'],
		then: openDetail('risk-assessments', 'RA.2026.01')
	},
	{
		// The detail header is what `concepts/risk-assessments.md` needs; the
		// full page is dominated by metadata the prose already covers.
		slug: 'risk-scenarios-table',
		url: '/risk-assessments',
		usedBy: ['concepts/risk-assessments.md'],
		then: openDetail('risk-assessments', 'RA.2026.01'),
		clip: (page) =>
			page
				.getByRole('heading', { name: 'Associated risk scenarios' })
				.locator('xpath=ancestor::div[contains(@class,"card")][1]')
	},
	{
		slug: 'applied-controls-full',
		url: '/applied-controls',
		usedBy: ['concepts/applied-controls.md'],
		fullPage: true
	},
	{
		slug: 'risk-matrices-list',
		url: '/risk-matrices',
		usedBy: ['concepts/libraries.md']
	},
	{
		// The concept page is about the grid, not the catalogue row — the list
		// view shows none of the anatomy the prose describes.
		slug: 'risk-matrix-detail',
		url: '/risk-matrices',
		usedBy: ['concepts/risk-matrices.md'],
		then: openDetail('risk-matrices', '5x5 ISO-27005'),
		// The route renders a raw field dump above the grid; anchor on the
		// matrix's own axis header and climb to the wrapper it is mounted in.
		clip: (page) =>
			page
				.locator('[data-testid="x-axis-header-0"]')
				// `wrapperClass` lands on the grid itself (RiskMatrix.svelte:160);
				// the axis titles and the risk-level legend are its siblings, so
				// the clip has to be the grid's parent.
				.locator('xpath=ancestor::div[contains(@class,"mt-8")][1]/..')
	},
	{
		slug: 'libraries-catalog',
		url: '/libraries',
		usedBy: ['concepts/libraries.md', 'guides/initial-setup.md']
	}
];
