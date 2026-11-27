import type { Locator, Page } from '@playwright/test';

export interface Shot {
	/** Output file name, without extension. Becomes `.gitbook/assets/<slug>.png`. */
	slug: string;
	/** Route to open, relative to the app root. */
	url: string;
	/** Which doc pages consume this image — kept here so a stale shot is traceable. */
	usedBy: string[];
	/** Frame size for this shot, set before the route loads. Defaults to the config's 1440×900. */
	viewport?: { width: number; height: number };
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
	/** Undo what `act` changed in the fixture; runs even when the capture fails. */
	cleanup?: (page: Page) => Promise<void>;
}

export interface Annotation {
	at: Locator;
	label?: string;
	/** Put the badge on the top-right corner, when the top-left one would cover a field label. */
	badgeRight?: boolean;
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

/** Tick one option of a scenario selection filter, the way a reader would. */
async function pickScenarios(page: Page, filter: string, option: string) {
	await page.getByTestId(`selection-filter-${filter}`).click();
	await page.getByTestId('selection-option').filter({ hasText: option }).first().click();
	await page.keyboard.press('Escape');
	await page.waitForLoadState('networkidle');
	// Closing hands focus back to the filter: drop its focus ring from the shot.
	await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
}

/** The AI assistant shots follow the reader's path from the sidebar, so they need a taller frame. */
const AI_SHOT_VIEWPORT = { width: 1440, height: 1200 };

/** On /settings the sidebar opens Extra by itself; scroll it so Extra and Settings sit near its bottom. */
async function showSettingsInSidebar(page: Page) {
	await page
		.locator('nav a[href="/settings"]')
		.first()
		.evaluate((link) => {
			const nav = link.closest('nav');
			if (nav)
				nav.scrollTop +=
					link.getBoundingClientRect().bottom - nav.getBoundingClientRect().bottom + 160;
		});
}

function sidebarPath(page: Page): Annotation[] {
	return [
		{
			at: page.locator('#extra').getByRole('button', { name: 'Extra' }),
			label: '1',
			badgeRight: true
		},
		{ at: page.locator('nav a[href="/settings"]').first(), label: '2', badgeRight: true }
	];
}

/** The Chat mode card; it carries the gradient classes only while checked. */
function chatModeCard(page: Page) {
	return page
		.getByText('Chat mode', { exact: true })
		.locator('xpath=ancestor::*[.//*[contains(text(),"Enable the chat assistant icon")]][1]');
}

/** Tick or untick Chat mode on the Feature flags tab and save, whatever state the flag is in. */
async function setChatMode(page: Page, on: boolean) {
	await page.goto('/settings?tab=featureFlags');
	await page.locator('body[data-hydrated="true"]').waitFor();
	await page.getByPlaceholder('Search...').fill('chat');
	const checked = /from-primary-400/.test((await chatModeCard(page).getAttribute('class')) ?? '');
	if (checked !== on) {
		await chatModeCard(page).click();
		await page.getByRole('button', { name: 'Save', exact: true }).click();
		await page.waitForLoadState('networkidle');
	}
}

const HEADER_CLEARANCE = 176;

/**
 * The app scrolls an inner container, not the document, so a viewport shot
 * stays on the page header unless that container is moved. Brings `target`
 * just under the sticky header.
 */
async function scrollUnderHeader(target: Locator, top = HEADER_CLEARANCE) {
	await target.waitFor();
	await target.evaluate((el, top) => {
		let scroller = el.parentElement;
		while (
			scroller &&
			!(
				scroller.scrollHeight > scroller.clientHeight + 4 &&
				/auto|scroll/.test(getComputedStyle(scroller).overflowY)
			)
		) {
			scroller = scroller.parentElement;
		}
		const box = scroller ?? document.scrollingElement;
		if (box) box.scrollTop += el.getBoundingClientRect().top - top;
	}, top);
}

/**
 * A clip taller than the viewport is stitched from several scrolls, and the
 * sticky page header lands in the middle of it. Grow the viewport until
 * `target` fits under that header in one piece.
 */
async function fitUnderHeader(page: Page, target: Locator) {
	await target.waitFor();
	const { width, height } = page.viewportSize() ?? { width: 1440, height: 900 };
	const needed = Math.ceil((await target.boundingBox())?.height ?? 0) + 2 * HEADER_CLEARANCE;
	if (needed > height) await page.setViewportSize({ width, height: needed });
	await scrollUnderHeader(target);
}

/** RA.2026.01 with its scenarios narrowed to one current risk level. */
async function openSelection(page: Page) {
	await openDetail('risk-assessments', 'RA.2026.01')(page);
	// The full label: "high" alone also matches "5 - very high".
	await pickScenarios(page, 'current_level', '4 - high');
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
		slug: 'control-plan',
		// A fixed window: the rolling default follows today and drifts past the fixture's dates.
		url: '/tasks-review?start_month=3&start_year=2026&end_month=12&end_year=2026',
		usedBy: ['features/control-plan.md'],
		act: async (page) => {
			await page.getByTestId('control-plan-preset-thisYear').waitFor();
		}
	},
	{
		slug: 'audit-tree-filters',
		url: '/compliance-assessments',
		usedBy: ['concepts/audits.md'],
		act: async (page) => {
			await openDetail('compliance-assessments', 'AUD.2026.01')(page);
			await page.getByRole('button', { name: 'Filters' }).first().click();
			await page.locator('[data-scope="popover"][data-part="content"]').first().waitFor();
		},
		clip: (page) => page.locator('[data-scope="popover"][data-part="content"]').first()
	},
	{
		slug: 'audit-export-options',
		url: '/compliance-assessments',
		usedBy: ['concepts/audits.md'],
		act: async (page) => {
			await openDetail('compliance-assessments', 'AUD.2026.01')(page);
			await page.getByTestId('export-button').click();
			await page.getByTestId('export-modal').waitFor();
		},
		clip: (page) => page.getByTestId('export-modal')
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
		act: async (page) => {
			await openDetail('risk-assessments', 'RA.2026.01')(page);
			await fitUnderHeader(
				page,
				page
					.getByRole('heading', { name: 'Associated risk scenarios' })
					.locator('xpath=ancestor::div[contains(@class,"card")][1]')
			);
		},
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
		// Selection applied: the bar, its counter and the narrowed table.
		slug: 'scenario-selection-bar',
		url: '/risk-assessments',
		usedBy: ['features/scenario-selection.md'],
		act: async (page) => {
			await openSelection(page);
			await scrollUnderHeader(page.getByTestId('scenario-selection-bar'));
		}
	},
	{
		// A filter open, for the per-option counts.
		slug: 'scenario-selection-filter',
		url: '/risk-assessments',
		usedBy: ['features/scenario-selection.md'],
		act: async (page) => {
			await openSelection(page);
			await scrollUnderHeader(page.getByTestId('scenario-selection-bar'));
			await page.getByTestId('selection-filter-treatment').click();
			await page.getByTestId('selection-option').first().waitFor();
		}
	},
	{
		slug: 'scenario-selection-matrix',
		url: '/risk-assessments',
		usedBy: ['features/scenario-selection.md'],
		// The badge and the current risk matrix: the residual one sits below.
		act: async (page) => {
			await openSelection(page);
			await scrollUnderHeader(
				page
					.getByTestId('matrix-selection-badge')
					.locator('xpath=ancestor::div[contains(@class,"card")][1]')
			);
		}
	},
	{
		slug: 'scenario-selection-export',
		url: '/risk-assessments',
		usedBy: ['features/scenario-selection.md'],
		act: async (page) => {
			await openSelection(page);
			await page.getByTestId('export-button').click();
			await page.getByTestId('export-apply-selection').waitFor();
		},
		clip: (page) => page.getByTestId('export-modal')
	},
	{
		// Reached through the button, which is what carries the selection over.
		slug: 'scenario-selection-action-plan',
		url: '/risk-assessments',
		usedBy: ['features/scenario-selection.md', 'features/action-plans.md'],
		act: async (page) => {
			await openSelection(page);
			await page.getByTestId('action-plan-button').click();
			await page.getByTestId('link-type-toggle').waitFor();
			// Folded, the budget overview leaves room for the measures table.
			await page.getByRole('button', { name: 'Budget overview' }).click();
		}
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
			// The whole page at a 16-inch MacBook's default size, so the strip is seen where it lives.
			await page.setViewportSize({ width: 1728, height: 1117 });
			await page.getByTestId('record-value-input').fill('1310');
		}
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
	},
	// Saves chat_mode so the chat icon shows, and turns it back off in cleanup.
	{
		slug: 'ai-assistant-feature-flag',
		viewport: AI_SHOT_VIEWPORT,
		url: '/settings',
		usedBy: ['integrations/ai-assistant-setup.md'],
		act: async (page) => {
			await setChatMode(page, true);
			await page.reload();
			await page.locator('body[data-hydrated="true"]').waitFor();
			await page.evaluate(() => document.fonts.ready);
			await page.getByPlaceholder('Search...').fill('chat');
			await page.getByRole('button', { name: 'Open chat assistant' }).waitFor();
			await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
			await showSettingsInSidebar(page);
		},
		annotate: (page) => [
			...sidebarPath(page),
			{ at: page.getByRole('tab', { name: 'Feature flags' }), label: '3' },
			{ at: page.getByPlaceholder('Search...'), label: '4' },
			{ at: chatModeCard(page), label: '5' },
			{ at: page.getByRole('button', { name: 'Save', exact: true }), label: '6' },
			{ at: page.getByRole('button', { name: 'Open chat assistant' }), label: '7' }
		],
		cleanup: (page) => setChatMode(page, false)
	},
	// Fills the form without saving.
	{
		slug: 'ai-assistant-model-settings',
		viewport: AI_SHOT_VIEWPORT,
		url: '/settings',
		usedBy: ['integrations/ai-assistant-setup.md'],
		act: async (page) => {
			const section = page.getByRole('button', { name: 'Chat / AI assistant' });
			await section.click();
			await page.locator('select[name="llm_provider"]').selectOption('openai_compatible');
			await page
				.locator('input[name="openai_api_base"]')
				.fill('https://oai.endpoints.kepler.ai.cloud.ovh.net/v1');
			await page.locator('input[name="openai_model"]').fill('gpt-oss-120b');
			await page.locator('input[name="openai_api_key"]').fill('xxxxxxxxxxxxxxxx');
			await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
			// Keep the other General sections in frame above it, as the reader sees them.
			await scrollUnderHeader(section, 560);
			await showSettingsInSidebar(page);
		},
		annotate: (page) => [
			...sidebarPath(page),
			{
				at: page.getByRole('button', { name: 'Chat / AI assistant' }),
				label: '3',
				badgeRight: true
			},
			{ at: page.locator('select[name="llm_provider"]'), label: '4', badgeRight: true },
			{ at: page.locator('input[name="openai_api_base"]'), label: '5', badgeRight: true },
			{ at: page.locator('input[name="openai_model"]'), label: '6', badgeRight: true },
			{ at: page.locator('input[name="openai_api_key"]'), label: '7', badgeRight: true },
			{ at: page.getByRole('button', { name: 'Save', exact: true }), label: '8' }
		]
	}
];
