/**
 * The vulnerability page: its summary card (severity, SLA state, timeline),
 * "Assigned to", the link tabs, and the SLA filter of the list.
 *
 * Objects are created through the API so each test controls the dates the SLA
 * state is computed from.
 */

import { test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import type { APIRequestContext, BrowserContext } from '@playwright/test';

const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

const DAY_MS = 86_400_000;
/** A calendar day relative to today, as the API's YYYY-MM-DD. */
const isoDay = (offset: number) =>
	new Date(Date.now() + offset * DAY_MS).toLocaleDateString('en-CA');

async function api(context: BrowserContext, request: APIRequestContext) {
	const token = (await context.cookies()).find((c) => c.name === 'token')?.value;
	if (!token) throw new Error('No `token` cookie found — is the user logged in?');
	const headers = { 'Content-Type': 'application/json', Authorization: `Token ${token}` };

	const folders = await request.get(`${BACKEND_API_URL}/folders/?content_type=GL`, { headers });
	const folder = (await folders.json()).results[0].id;

	const call = async (method: 'get' | 'post' | 'patch' | 'put', path: string, data?: object) => {
		const res = await request[method](`${BACKEND_API_URL}/${path}`, { data, headers });
		expect(res.ok(), `${method.toUpperCase()} ${path}: ${res.status()} ${await res.text()}`).toBe(
			true
		);
		return res.json();
	};
	const create = (model: string, data: Record<string, unknown>) =>
		call('post', `${model}/`, { folder, ...data });
	// The feature-flags suite turns Vulnerabilities off and back on, which leaves
	// the SLA flag off. The endpoint replaces the whole set, so send it all back.
	const enableSla = async () => {
		const flags = await call('get', 'settings/feature-flags/');
		if (!flags.vulnerability_sla) {
			await call('put', 'settings/feature-flags/', { ...flags, vulnerability_sla: true });
		}
	};
	return { call, create, enableSla };
}

test('the summary card shows severity, status, SLA state and dates in order', async ({
	logedPage,
	page,
	context
}) => {
	const { call, create, enableSla } = await api(context, page.request);
	await enableSla();
	const actor = (await call('get', 'actors/?search=admin@tests.com')).results[0];
	const vulnerability = await create('vulnerabilities', {
		name: `Summary card ${Date.now()}`,
		severity: 4,
		status: 'exploitable',
		detected_at: isoDay(-10),
		due_date: isoDay(-2),
		owner: [actor.id]
	});

	await page.goto(`/vulnerabilities/${vulnerability.id}`);
	await page.waitForLoadState('networkidle');

	const card = page.getByTestId('vulnerability-summary');
	await expect(card.getByTestId('vulnerability-severity-badge')).toContainText(/critical/i);
	await expect(card.getByTestId('vulnerability-status-badge')).toHaveText(m.exploitable());
	await expect(card.getByTestId('vulnerability-sla-state')).toContainText(m.overdue());
	await expect(card.getByTestId('vulnerability-sla-state')).toContainText(
		m.vulnerabilitySlaDaysLate({ count: 2 })
	);
	// The card shows them, so the field list doesn't repeat them.
	await expect(page.getByTestId('status-field-title')).toHaveCount(0);
	await expect(page.getByTestId('severity-field-title')).toHaveCount(0);
	const events = await card
		.getByTestId('vulnerability-timeline')
		.locator('li[data-testid^="timeline-"]')
		.evaluateAll((items) => items.map((item) => item.getAttribute('data-testid')));
	expect(events).toEqual(['timeline-detected_at', 'timeline-due_date', 'timeline-today']);
	await expect(card.getByTestId('timeline-due_date')).toContainText(m.overdue());
	await expect(card.getByTestId('vulnerability-duration')).toHaveText(
		m.vulnerabilityOpenForDays({ count: 10 })
	);

	const ownerName = (await call('get', `vulnerabilities/${vulnerability.id}/`)).owner[0].str;
	await expect(page.getByTestId('owner-field-value')).toContainText(ownerName);
});

test('link tabs offer select-existing and create, read-only ones neither', async ({
	logedPage,
	page,
	context
}) => {
	const { create } = await api(context, page.request);
	const vulnerability = await create('vulnerabilities', { name: `Link tabs ${Date.now()}` });

	await page.goto(`/vulnerabilities/${vulnerability.id}`);
	await page.waitForLoadState('networkidle');

	for (const name of [
		'Assets',
		'Applied controls',
		'Exceptions',
		'Evidences',
		'Tasks',
		'Incidents'
	]) {
		await page.getByRole('tab', { name: new RegExp(`^${name}`) }).click();
		const panel = page.getByRole('tabpanel', { name: new RegExp(`^${name}`) });
		await expect(panel.getByTestId('select-existing-button'), name).toBeVisible();
		await expect(panel.getByTestId('add-button'), name).toBeVisible();
	}
	// Linked from the other side: shown here, edited there.
	for (const name of ['Risk scenarios', 'Findings']) {
		await page.getByRole('tab', { name: new RegExp(`^${name}`) }).click();
		const panel = page.getByRole('tabpanel', { name: new RegExp(`^${name}`) });
		await expect(panel.locator('table')).toBeVisible();
		await expect(panel.getByTestId('select-existing-button'), name).toHaveCount(0);
		await expect(panel.getByTestId('add-button'), name).toHaveCount(0);
	}
});

/**
 * The select-existing modal PATCHes the whole relation, seeded from the update
 * form: a field its schema doesn't declare would replace the links instead of
 * extending them. Assets are a field of the vulnerability, incidents point at
 * it from the other side, so each kind is covered.
 */
for (const { tab, field } of [
	{ tab: 'Assets', field: 'assets' },
	{ tab: 'Incidents', field: 'incidents' }
]) {
	test(`attaching ${field} keeps the ones already linked`, async ({ logedPage, page, context }) => {
		const { call, create } = await api(context, page.request);
		const suffix = Date.now();
		const first = await create(field, { name: `First ${field} ${suffix}` });
		const second = await create(field, { name: `Second ${field} ${suffix}` });
		const vulnerability = await create('vulnerabilities', { name: `Keeps ${field} ${suffix}` });
		await call('patch', `vulnerabilities/${vulnerability.id}/`, { [field]: [first.id] });

		await page.goto(`/vulnerabilities/${vulnerability.id}`);
		await page.waitForLoadState('networkidle');

		await page.getByRole('tab', { name: new RegExp(`^${tab}`) }).click();
		const panel = page.getByRole('tabpanel', { name: new RegExp(`^${tab}`) });
		await expect(panel.getByText(first.name)).toBeVisible();

		await panel.getByTestId('select-existing-button').click();
		await expect(page.getByTestId('modal-title')).toBeVisible();
		// Click the search box itself: the field's centre can be the remove
		// button of the chip already selected.
		const search = page.getByTestId(`form-input-${field}`).getByRole('combobox');
		await search.click();
		await search.fill(second.name);
		await page
			.getByRole('option', { name: new RegExp(second.name) })
			.first()
			.click();
		// The option list stays open over the modal footer: dismiss it first.
		await page.getByTestId('modal-title').click();
		await page.locator('.modal-example-form').getByRole('button', { name: m.save() }).click();

		await expect(panel.getByText(second.name)).toBeVisible();
		await expect(panel.getByText(first.name)).toBeVisible();
	});
}

test('the SLA filter lists the vulnerabilities in that state', async ({
	logedPage,
	page,
	context
}) => {
	const { create, enableSla } = await api(context, page.request);
	await enableSla();
	const suffix = Date.now();
	const overdue = await create('vulnerabilities', {
		name: `Overdue ${suffix}`,
		severity: 4,
		due_date: isoDay(-3)
	});
	const onTrack = await create('vulnerabilities', {
		name: `On track ${suffix}`,
		severity: 4,
		due_date: isoDay(30)
	});

	await page.goto('/vulnerabilities?state=overdue');
	await page.waitForLoadState('networkidle');

	await expect(page.getByText(overdue.name)).toBeVisible();
	await expect(
		page
			.getByRole('row')
			.filter({ hasText: overdue.name })
			.getByTestId('vulnerability-sla-countdown')
	).toHaveText(m.vulnerabilitySlaDaysLate({ count: 3 }));
	await expect(page.getByText(onTrack.name)).toHaveCount(0);
});
