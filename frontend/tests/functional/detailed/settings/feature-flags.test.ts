import { LoginPage } from '../../../utils/login-page.js';
import { test, expect, type Page } from '../../../utils/test-utils.js';
import { PageContent } from '../../../utils/page-content.js';

const sidebar = (page: Page) => page.getByTestId('sidebar');

const gotoFeatureFlags = async (page: Page) => {
	await page.goto('/settings');
	await page.waitForLoadState('networkidle');

	const tab = page.getByRole('tab', { name: /feature flags/i });
	await expect(tab).toBeVisible();
	await tab.click();

	await expect(page.locator('[role="checkbox"]').first()).toBeVisible();
};

/** Enable or disable a feature flag by its label, then save. */
const setFlag = async (page: Page, flagLabel: string, enable: boolean) => {
	await gotoFeatureFlags(page);

	const panel = page.locator('[id$="content-featureFlags"]');
	const panelExists = (await panel.count()) > 0;
	const scope = panelExists ? panel : page;

	const card = scope
		.locator('[role="checkbox"]')
		.filter({ has: page.locator('span.font-semibold', { hasText: flagLabel }) });

	await expect(card).toBeVisible();

	const isChecked = (await card.getAttribute('aria-checked')) === 'true';
	if (isChecked !== enable) {
		await card.click();
		await expect(card).toHaveAttribute('aria-checked', String(enable));
		await page.getByRole('button', { name: /save/i }).click();
		await expect(page.getByTestId('toast')).toBeVisible();
		await page.waitForLoadState('networkidle');
	}
};

// ---------------------------------------------------------------------------
// Flag labels — exact span.font-semibold text in the EN UI
// ---------------------------------------------------------------------------
const FLAGS = {
	// Operations
	xrays: 'X-rays',
	incidents: 'Incidents',
	tasks: 'Tasks',
	// Organization
	objectivesIso: 'Objectives (ISO)',
	issuesIso: 'Issues (ISO)',
	// Governance
	riskAcceptances: 'Risk acceptances',
	exceptions: 'Exceptions',
	followUp: 'Findings tracking',
	// Risk
	ebiosRm: 'Ebios RM',
	scoringAssistant: 'Scoring assistant',
	vulnerabilities: 'Vulnerabilities',
	// Top-level modules
	compliance: 'Compliance',
	tprm: 'Third party',
	// GDPR / Privacy
	privacy: 'Privacy',
	personalData: 'Personal Data',
	purposes: 'Purposes',
	rightRequests: 'Right Requests',
	dataBreaches: 'Data Breaches',
	// Extra
	terminologies: 'Terminologies',
	webhooks: 'Webhooks',
	journeys: 'Journeys',
	experimental: 'Experimental',
	// Inherent Risk
	inherentRisk: 'Inherent Risk'
} as const;

const SIDEBAR_TESTID: Record<keyof typeof FLAGS, string | null> = {
	xrays: 'accordion-item-x-rays',
	incidents: 'accordion-item-incidents',
	tasks: 'accordion-item-task-templates',
	objectivesIso: 'accordion-item-organisation-objectives',
	issuesIso: 'accordion-item-organisation-issues',
	riskAcceptances: 'accordion-item-risk-acceptances',
	exceptions: 'accordion-item-security-exceptions',
	followUp: 'accordion-item-findings-assessments',
	ebiosRm: 'accordion-item-ebios-rm',
	scoringAssistant: 'accordion-item-scoring-assistant',
	vulnerabilities: 'accordion-item-vulnerabilities',
	compliance: 'accordion-item-compliance',
	tprm: 'accordion-item-thirdpartycategory',
	privacy: 'accordion-item-privacy',
	personalData: 'accordion-item-personal-data',
	purposes: 'accordion-item-purposes',
	rightRequests: 'accordion-item-right-requests',
	dataBreaches: 'accordion-item-data-breaches',
	terminologies: 'accordion-item-terminologies',
	webhooks: null,
	journeys: 'accordion-item-presets',
	experimental: 'accordion-item-experimental',
	inherentRisk: null
};

const SIDEBAR_SECTION: Record<keyof typeof FLAGS, string | null> = {
	xrays: 'accordion-item-operations',
	incidents: 'accordion-item-operations',
	tasks: 'accordion-item-operations',
	objectivesIso: 'accordion-item-governance',
	issuesIso: 'accordion-item-governance',
	riskAcceptances: 'accordion-item-governance',
	exceptions: 'accordion-item-governance',
	followUp: 'accordion-item-governance',
	ebiosRm: 'accordion-item-risk',
	scoringAssistant: 'accordion-item-risk',
	vulnerabilities: 'accordion-item-risk',
	compliance: null,
	tprm: null,
	privacy: null,
	personalData: 'accordion-item-privacy',
	purposes: 'accordion-item-privacy',
	rightRequests: 'accordion-item-privacy',
	dataBreaches: 'accordion-item-privacy',
	terminologies: 'accordion-item-extra',
	webhooks: null,
	journeys: 'accordion-item-overview',
	experimental: 'accordion-item-extra',
	inherentRisk: null
};

const openSidebarSection = async (page: Page, sectionTestId: string | null) => {
	await page.goto('/analytics');
	await page.waitForLoadState('networkidle');
	if (sectionTestId) {
		const sectionSpan = sidebar(page).getByTestId(sectionTestId);
		const triggerBtn = sectionSpan.locator('..');
		const isExpanded = await triggerBtn.getAttribute('aria-expanded').catch(() => null);
		if (isExpanded !== 'true') {
			await sectionSpan.click();
		}
		await expect(triggerBtn).toHaveAttribute('aria-expanded', 'true');
	}
};

const testSidebarFlag = async (page: Page, flagKey: keyof typeof FLAGS) => {
	const flagLabel = FLAGS[flagKey];
	const sectionTestId = SIDEBAR_SECTION[flagKey];
	const itemTestId = SIDEBAR_TESTID[flagKey];

	if (itemTestId === null) {
		throw new Error(
			`testSidebarFlag called for "${flagKey}" which has no sidebar item. ` +
				`Write a dedicated test instead.`
		);
	}

	await setFlag(page, flagLabel, true);
	try {
		await openSidebarSection(page, sectionTestId);
		await expect(sidebar(page).getByTestId(itemTestId)).toBeVisible();

		await setFlag(page, flagLabel, false);
		await openSidebarSection(page, sectionTestId);
		await expect(sidebar(page).getByTestId(itemTestId)).not.toBeVisible();
	} finally {
		await setFlag(page, flagLabel, true);
	}
};

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

test.describe.configure({ mode: 'serial' });

test.describe('Feature flags', () => {
	let page: Page;

	test.beforeAll(async ({ browser }) => {
		const context = await browser.newContext({ locale: 'en-US' });
		page = await context.newPage();
		const loginPage = new LoginPage(page);
		await loginPage.goto();
		await loginPage.login();
		await loginPage.skipWelcome();
	});

	test.afterAll(async () => {
		await page.context().close();
	});

	// ---------- Operations ----------

	test('X-Rays visibility toggling', async () => {
		await testSidebarFlag(page, 'xrays');
	});

	test('Incidents visibility toggling', async () => {
		await testSidebarFlag(page, 'incidents');
	});

	test('Tasks visibility toggling', async () => {
		await testSidebarFlag(page, 'tasks');
	});

	// ---------- Organization ----------

	test('Objectives (ISO) visibility toggling', async () => {
		await testSidebarFlag(page, 'objectivesIso');
	});

	test('Issues (ISO) visibility toggling', async () => {
		await testSidebarFlag(page, 'issuesIso');
	});

	// ---------- Governance ----------

	test('Risk Acceptances visibility toggling', async () => {
		await testSidebarFlag(page, 'riskAcceptances');
	});

	test('Exceptions visibility toggling', async () => {
		await testSidebarFlag(page, 'exceptions');
	});

	test('Findings Tracking visibility toggling', async () => {
		await testSidebarFlag(page, 'followUp');
	});

	// ---------- Risk ----------

	test('Ebios RM visibility toggling', async () => {
		await testSidebarFlag(page, 'ebiosRm');
	});

	test('Scoring Assistant visibility toggling', async () => {
		await testSidebarFlag(page, 'scoringAssistant');
	});

	test('Vulnerabilities visibility toggling', async () => {
		await testSidebarFlag(page, 'vulnerabilities');
	});

	// ---------- Top-level modules ----------

	test('Compliance visibility toggling', async () => {
		await testSidebarFlag(page, 'compliance');
	});

	test('Third Party visibility toggling', async () => {
		await testSidebarFlag(page, 'tprm');
	});

	// ---------- GDPR / Privacy ----------

	test('Privacy module visibility toggling', async () => {
		await testSidebarFlag(page, 'privacy');
	});

	test('Personal Data visibility toggling', async () => {
		await setFlag(page, FLAGS.privacy, true);
		await testSidebarFlag(page, 'personalData');
	});

	test('Purposes visibility toggling', async () => {
		await setFlag(page, FLAGS.privacy, true);
		await testSidebarFlag(page, 'purposes');
	});

	test('Right Requests visibility toggling', async () => {
		await setFlag(page, FLAGS.privacy, true);
		await testSidebarFlag(page, 'rightRequests');
	});

	test('Data Breaches visibility toggling', async () => {
		await setFlag(page, FLAGS.privacy, true);
		await testSidebarFlag(page, 'dataBreaches');
	});

	// ---------- Extra ----------

	test('Terminologies visibility toggling', async () => {
		await testSidebarFlag(page, 'terminologies');
	});

	test('Webhooks adds a tab in Settings', async () => {
		await setFlag(page, FLAGS.webhooks, true);
		try {
			await page.goto('/settings');
			await page.waitForLoadState('networkidle');
			await expect(page.locator('[data-value="webhooks"]')).toBeVisible();

			await setFlag(page, FLAGS.webhooks, false);
			await page.goto('/settings');
			await page.waitForLoadState('networkidle');
			await expect(page.locator('[data-value="webhooks"]')).not.toBeVisible();
		} finally {
			await setFlag(page, FLAGS.webhooks, true);
		}
	});

	test('Journeys visibility toggling', async () => {
		await testSidebarFlag(page, 'journeys');
	});

	test('Experimental visibility toggling', async () => {
		await testSidebarFlag(page, 'experimental');
	});

	// ---------- Inherent Risk (no sidebar item) ----------

	test('Inherent Risk visibility on Risk Scenarios table view', async () => {
		const risksPage = new PageContent(page, '/risk-scenarios', 'Risk Scenarios');

		await setFlag(page, FLAGS.inherentRisk, true);
		try {
			await risksPage.goto();
			await expect(page.getByText('Inherent Level', { exact: true })).toBeVisible();

			await setFlag(page, FLAGS.inherentRisk, false);
			await risksPage.goto();
			await expect(page.getByText('Inherent Level', { exact: true })).not.toBeVisible();
		} finally {
			await setFlag(page, FLAGS.inherentRisk, true);
		}
	});
});
