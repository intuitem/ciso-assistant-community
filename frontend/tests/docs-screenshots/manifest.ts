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
	act?: (page: Page) => Promise<void>;
	/**
	 * Draw callout boxes over elements before capturing — the annotated,
	 * step-by-step genre the Guidde frames use. Each entry outlines its target;
	 * a `label` adds a numbered badge so the prose can refer to it.
	 */
	annotate?: (page: Page) => Annotation[];
}

export interface Annotation {
	at: Locator;
	label?: string;
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
		act: openDetail('compliance-assessments', 'AUD.2026.01')
	},
	{
		slug: 'risk-assessment-detail',
		url: '/risk-assessments',
		usedBy: ['concepts/risk-assessments.md', 'guides/first-risk-assessment.md'],
		act: openDetail('risk-assessments', 'RA.2026.01')
	},
	{
		// The detail header is what `concepts/risk-assessments.md` needs; the
		// full page is dominated by metadata the prose already covers.
		slug: 'risk-scenarios-table',
		url: '/risk-assessments',
		usedBy: ['concepts/risk-assessments.md'],
		act: openDetail('risk-assessments', 'RA.2026.01'),
		clip: (page) =>
			page
				.getByRole('heading', { name: 'Associated risk scenarios' })
				.locator('xpath=ancestor::div[contains(@class,"card")][1]')
	},
	{
		// Annotated variant, for the step-by-step guide genre. Labels are the
		// step numbers the surrounding prose refers to.
		slug: 'risk-assessment-annotated',
		url: '/risk-assessments',
		usedBy: ['guides/first-risk-assessment.md'],
		act: openDetail('risk-assessments', 'RA.2026.01'),
		annotate: (page) => [
			{ at: page.getByRole('link', { name: 'Action plan' }).first(), label: '1' },
			{ at: page.getByRole('button', { name: 'Add risk scenario' }).first(), label: '2' }
		]
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
		act: openDetail('risk-matrices', '5x5 ISO-27005'),
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
	},
	{
		slug: 'dpia-overview',
		url: '/dpias',
		usedBy: ['concepts/dpia.md', 'guides/dpia.md'],
		act: async (page) => {
			await page.getByRole('button', { name: 'Toggle sidebar' }).click();
		},
		fullPage: true
	},
	{
		slug: 'dpia-screening-card',
		url: '/processings',
		usedBy: ['concepts/dpia.md', 'guides/dpia.md'],
		act: openDetail('processings', 'ROPA-002'),
		clip: (page) => page.getByTestId('dpia-screening-card')
	},
	{
		slug: 'dpia-privacy-risk',
		url: '/processings',
		usedBy: ['concepts/dpia.md', 'guides/dpia.md'],
		act: async (page) => {
			await openDetail('processings', 'ROPA-002')(page);
			await page.getByTestId('dpia-link').click();
			await page.locator('body[data-hydrated="true"]').waitFor();
			await page.getByRole('button', { name: 'Results' }).click();
		},
		clip: (page) =>
			page
				.getByText('Privacy risk', { exact: true })
				.locator('xpath=ancestor::div[contains(@class,"card")][1]')
	},
	{
		slug: 'processor-register',
		url: '/processings',
		usedBy: ['concepts/privacy-register.md'],
		act: async (page) => {
			await page.getByRole('button', { name: 'Processor register' }).click();
			await page.locator('tr', { hasText: 'ROPA-012' }).waitFor();
		},
		clip: (page) =>
			page
				.getByRole('button', { name: 'Processor register' })
				.locator('xpath=ancestor::div[contains(@class,"card")][1]')
	},
	// ---- metrics: one-step creation, recording, merge, widgets (attach mode, dev data) ----
	{
		slug: 'metrics-new-metric',
		url: '/metric-instances',
		usedBy: ['features/metrics/creating-a-metric.md', 'concepts/metrics.md'],
		act: async (page) => {
			// The form is taller than the default viewport; show it whole.
			await page.setViewportSize({ width: 1440, height: 1180 });
			await page.getByRole('button', { name: 'Add a metric instance' }).click();
			const dialog = page.getByRole('dialog').last();
			await dialog.getByTestId('form-input-name').fill('Number of assets');
			await dialog.getByRole('button', { name: 'Domain' }).click();
			await dialog.getByPlaceholder('Search...').fill('Spain');
			await dialog.getByRole('option', { name: /ACME Spain/ }).click();
			await dialog.getByRole('combobox', { name: 'Unit' }).fill('Count');
			await page.getByRole('option', { name: 'Count', exact: true }).first().click();
			await page.getByTestId('similar-definition-hint').waitFor();
			await page.getByTestId('similar-definition-hint').scrollIntoViewIfNeeded();
		},
		// The outer dialog: the inner one re-renders as the form settles.
		clip: (page) => page.getByRole('dialog').first()
	},
	{
		slug: 'metrics-new-metric-from-definition',
		url: '/metric-instances',
		usedBy: ['features/metrics/creating-a-metric.md'],
		act: async (page) => {
			// The form is taller than the default viewport; show it whole.
			await page.setViewportSize({ width: 1440, height: 1180 });
			await page.getByRole('button', { name: 'Add a metric instance' }).click();
			const dialog = page.getByRole('dialog').last();
			await dialog.getByRole('button', { name: 'Domain' }).click();
			await dialog.getByPlaceholder('Search...').fill('Spain');
			await dialog.getByRole('option', { name: /ACME Spain/ }).click();
			await dialog.getByRole('radio', { name: 'Use an existing definition' }).click();
			await dialog.getByRole('combobox', { name: 'Metric definition' }).fill('Training');
			await page
				.getByRole('option', { name: /Training coverage/ })
				.first()
				.click();
			await page.getByTestId('copied-from-definition').waitFor();
			await page.getByTestId('copied-from-definition').scrollIntoViewIfNeeded();
		},
		// The outer dialog: the inner one re-renders as the form settles.
		clip: (page) => page.getByRole('dialog').first()
	},
	{
		slug: 'metrics-record-value',
		url: '/metric-instances/597d588f-e161-46e5-9f66-53f7b632bfc2',
		usedBy: ['features/metrics/recording-values.md', 'concepts/metrics.md'],
		act: async (page) => {
			await page.getByTestId('record-value-input').fill('1310');
		},
		clip: (page) => page.getByTestId('record-value-strip')
	},
	{
		slug: 'metrics-merge',
		url: '/metric-definitions/f2355942-3463-47b1-85a2-f072784290c2',
		usedBy: ['features/metrics/creating-a-metric.md'],
		act: async (page) => {
			await page.getByTestId('merge-definition-button').click();
			await page.getByTestId('merge-definition-modal').getByRole('radio').first().click();
		},
		clip: (page) => page.getByTestId('merge-definition-modal')
	},
	{
		slug: 'metrics-widget-preview',
		url: '/dashboards/84d92700-b6a1-4641-aa2c-e4648f80c2f2/layout',
		usedBy: ['features/dashboards.md'],
		act: async (page) => {
			await page.getByRole('button', { name: 'Add custom metric' }).click();
			const dialog = page.getByRole('dialog').last();
			await page.setViewportSize({ width: 1440, height: 1000 });
			await dialog.getByRole('combobox', { name: 'Metric Instance' }).fill('Training');
			await page
				.getByRole('option', { name: /Training coverage/ })
				.first()
				.click();
			await dialog
				.locator('select')
				.filter({ has: page.locator('option[value="line"]') })
				.selectOption('line');
			await dialog
				.locator('select')
				.filter({ has: page.locator('option[value="all_time"]') })
				.selectOption('all_time');
			await dialog.getByRole('checkbox').first().check();
			// ECharts renders the preview as an SVG image.
			await dialog
				.getByTestId('widget-preview')
				.locator('svg, canvas')
				.first()
				.waitFor({ state: 'attached' });
			// ECharts draws a frame after it measures its container.
			await page.waitForTimeout(1500);
		},
		// The outer dialog: the inner one re-renders as the form settles.
		clip: (page) => page.getByRole('dialog').first()
	},
	{
		slug: 'metrics-widget-link',
		url: '/dashboards/84d92700-b6a1-4641-aa2c-e4648f80c2f2',
		usedBy: ['features/dashboards.md'],
		act: async (page) => {
			await page.getByTestId('widget-source-link').first().hover();
		},
		clip: (page) =>
			page
				.getByTestId('widget-source-link')
				.first()
				.locator('xpath=ancestor::div[contains(@class,"card")][1]')
	}
];
