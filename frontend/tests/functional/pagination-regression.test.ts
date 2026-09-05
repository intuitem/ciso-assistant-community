/**
 * Pagination regression harness.
 *
 * The suite's seed data never exceeds one page, so a first-page-only consumer
 * still passes CI. e2e-tests.sh pins PAGINATE_BY=100; these tests then create
 * more than one page through the API and drive the UI:
 *
 *   1. picker search must reach options beyond the first page,
 *   2. m2m links beyond one hydration chunk must survive an unrelated save,
 *   3. ListSelector must render the full option list.
 */

import { randomBytes } from 'crypto';
import { LoginPage } from '../utils/login-page.js';
import { test, expect, getUniqueValue, type Page } from '../utils/test-utils.js';
import type { BrowserContext } from '@playwright/test';

/** Resolve the backend base URL the SvelteKit app was built with. */
const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

/** Default backend page size — objects created must exceed this. */
const PAGE_SIZE = 100;
const SEED_COUNT = 60;

/** Extract the auth token the frontend stored after login. */
async function getAuthToken(context: BrowserContext): Promise<string> {
	const cookies = await context.cookies();
	const token = cookies.find((c) => c.name === 'token')?.value;
	if (!token) throw new Error('No `token` cookie found — is the user logged in?');
	return token;
}

function authHeaders(token: string) {
	return {
		'Content-Type': 'application/json',
		Authorization: `Token ${token}`
	};
}

async function apiGet(page: Page, token: string, path: string) {
	const response = await page.request.get(`${BACKEND_API_URL}${path}`, {
		headers: authHeaders(token)
	});
	expect(
		response.ok(),
		`GET ${path} failed: ${response.status()} ${await response.text()}`
	).toBeTruthy();
	return response.json();
}

async function apiPost(page: Page, token: string, path: string, data: Record<string, any>) {
	const response = await page.request.post(`${BACKEND_API_URL}${path}`, {
		data,
		headers: authHeaders(token)
	});
	expect(
		response.ok(),
		`POST ${path} failed: ${response.status()} ${await response.text()}`
	).toBeTruthy();
	return response.json();
}

/**
 * Create a user and return its id. When no mail server is reachable the
 * backend answers 400 with a "warning" but still creates the user — recover
 * by looking the user up by email.
 */
async function apiCreateUser(page: Page, token: string, email: string): Promise<string> {
	const response = await page.request.post(`${BACKEND_API_URL}/users/`, {
		data: { email },
		headers: authHeaders(token)
	});
	if (response.ok()) return (await response.json()).id;
	const body = await response.text();
	expect(
		response.status() === 400 && body.includes('warning'),
		`POST /users/ failed: ${response.status()} ${body}`
	).toBeTruthy();
	const found = await apiGet(page, token, `/users/?search=${encodeURIComponent(email)}`);
	const user = (found.results ?? found).find((u: any) => u.email === email);
	expect(user, `user ${email} not found after creation`).toBeTruthy();
	return user.id;
}

// Ids created by the tests, deleted in afterAll. Domains cascade-delete
// everything they contain, so per-test objects only need their domain here.
const createdFolderIds: string[] = [];
const createdUserIds: string[] = [];
const createdRoleIds: string[] = [];

async function createDomain(
	page: Page,
	token: string,
	name: string,
	createIamGroups = false
): Promise<string> {
	const folder = await apiPost(page, token, '/folders/', {
		name,
		create_iam_groups: createIamGroups
	});
	createdFolderIds.push(folder.id);
	return folder.id;
}

/** Zero-padded suffix so names sort in creation order. */
const pad = (i: number) => String(i).padStart(3, '0');

/** Per-run suffix keeping object names unique across (possibly dirty) runs. */
const suffix = randomBytes(3).toString('hex');

test('lazy picker search finds a user group beyond the first page', async ({ logedPage, page }) => {
	test.slow();
	const token = await getAuthToken(page.context());

	// User groups cannot be created directly (no role carries add_usergroup:
	// they are only provisioned automatically), so seed them through domains
	// with create_iam_groups — each such domain provisions 6 builtin groups.
	// 10 filler domains -> 60 groups that both sort (name ordering, "aa-" <
	// "zz-") and were created (creation ordering) before the needle domain's
	// groups: whatever the backend orders by, the needle group is beyond the
	// first page of the unfiltered list.
	for (let i = 0; i < 10; i++) {
		await createDomain(page, token, `aa-pagination-filler-${pad(i)}-${suffix}`, true);
	}
	const needleName = `zz-pagination-needle-${suffix}`;
	await createDomain(page, token, needleName, true);

	// A throwaway user whose edit form carries the user-group picker.
	const email = getUniqueValue('pagination-picker@tests.com');
	const userId = await apiCreateUser(page, token, email);
	createdUserIds.push(userId);

	await page.goto(`/users/${userId}/edit`);
	await page.locator('body[data-hydrated="true"]').waitFor();

	const groupsField = page.getByTestId('form-input-user-groups');
	await groupsField.click();
	await groupsField.getByRole('combobox').fill(needleName);

	// A first-page-only consumer would filter only locally-known options and
	// never surface the needle.
	await expect(groupsField.getByRole('option', { name: needleName }).first()).toBeVisible();
});

test('m2m links beyond one page survive an edit-form save that does not touch them', async ({
	logedPage,
	page
}) => {
	test.slow();
	const token = await getAuthToken(page.context());
	const domainId = await createDomain(page, token, getUniqueValue('pagination-m2m-domain'));

	const evidenceIds: string[] = [];
	for (let i = 0; i < SEED_COUNT; i++) {
		const evidence = await apiPost(page, token, '/evidences/', {
			name: `pagination-evidence-${pad(i)}`,
			folder: domainId
		});
		evidenceIds.push(evidence.id);
	}

	const controlName = getUniqueValue('pagination-m2m-control');
	const control = await apiPost(page, token, '/applied-controls/', {
		name: controlName,
		folder: domainId,
		evidences: evidenceIds
	});

	await page.goto(`/applied-controls/${control.id}/edit`);
	await page.locator('body[data-hydrated="true"]').waitFor();

	// Hydration integrity: every linked evidence must be selected in the
	// picker, including those beyond the first page. Selected chips are plain
	// list items (no option role). Overflow chips stay in the DOM: the
	// component collapses them with CSS (chip-max-N) and turns one chip into a
	// "+N" badge, so count the <li>s. If svelte-multiselect's own
	// maxVisibleChips ever gets enabled, its "+N more" button would hide chips
	// from the DOM, so expand it first.
	const evidencesField = page.getByTestId('form-input-evidences');
	await expect(evidencesField).toBeVisible();
	const moreChips = evidencesField.locator('button.more-chips');
	await expect
		.poll(async () => {
			if (
				(await moreChips.count()) > 0 &&
				(await moreChips.getAttribute('aria-expanded')) !== 'true'
			) {
				await moreChips.click();
			}
			return evidencesField.locator('ul.selected li:not(.more-chip)').count();
		})
		.toBe(SEED_COUNT);
	await expect(
		evidencesField.locator('ul.selected li', {
			hasText: `pagination-evidence-${pad(SEED_COUNT - 1)}`
		})
	).toHaveCount(1);

	// Rename the control (a field unrelated to the m2m) so a successful save
	// round-trip is observable, then save WITHOUT touching evidences.
	const savedName = `${controlName}-saved`;
	await page.getByTestId('form-input-name').fill(savedName);
	const saveResponse = page.waitForResponse(
		(response) =>
			response.request().method() === 'POST' &&
			response.url().includes(`/applied-controls/${control.id}/edit`)
	);
	await page.getByTestId('save-button').click();
	expect((await saveResponse).ok()).toBeTruthy();
	await expect(page.getByTestId('toast').first()).toBeVisible();

	// The save must not have dropped any of the 60 links.
	const refetched = await apiGet(page, token, `/applied-controls/${control.id}/`);
	expect(refetched.name).toBe(savedName);
	expect(refetched.evidences.length).toBe(SEED_COUNT);
});

test('ListSelector renders the full permission list on the custom role form', async ({
	logedPage,
	page
}) => {
	test.slow();
	const token = await getAuthToken(page.context());

	// Roles and permissions endpoints only exist on the enterprise backend.
	const probe = await page.request.get(`${BACKEND_API_URL}/roles/`, {
		headers: authHeaders(token)
	});
	test.skip(!probe.ok(), 'roles/permissions endpoints are enterprise-only');

	const folders = await apiGet(page, token, '/folders/?limit=200');
	const globalFolder = (folders.results ?? folders).find(
		(folder: any) => folder.content_type === 'GL' || folder.name === 'Global'
	);
	expect(globalFolder, 'Global folder not found').toBeTruthy();

	const role = await apiPost(page, token, '/roles/', {
		name: getUniqueValue('pagination-custom-role'),
		folder: globalFolder.id
	});
	createdRoleIds.push(role.id);

	// The permission ListSelector renders on the role edit form.
	await page.goto(`/roles/${role.id}/edit`);
	await page.locator('body[data-hydrated="true"]').waitFor();
	await expect(page.getByTestId('loading-spinner')).toHaveCount(0);

	// Groups are collapsed by default: each top-level (app) header shows its
	// total option count as "(N)". Their sum is the full permission list.
	const groupCounts = page.locator('form span.text-xs').filter({ hasText: /^\(\d+\)$/ });
	await expect(groupCounts.first()).toBeVisible();
	const counts = await groupCounts.allTextContents();
	const totalPermissions = counts.reduce((sum, text) => sum + Number(text.match(/\d+/)![0]), 0);

	// Django ships hundreds of permissions — a first-page-only consumer
	// renders at most one page of them.
	expect(totalPermissions).toBeGreaterThan(PAGE_SIZE);
});

test.afterAll('cleanup', async ({ browser }) => {
	const page = await browser.newPage();
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	await loginPage.login();
	const token = await getAuthToken(page.context());

	// Roles first (enterprise cleans up the user groups it provisioned),
	// then users, then domains (cascade-delete their contents).
	for (const id of createdRoleIds) {
		await page.request.delete(`${BACKEND_API_URL}/roles/${id}/`, {
			headers: authHeaders(token)
		});
	}
	for (const id of createdUserIds) {
		await page.request.delete(`${BACKEND_API_URL}/users/${id}/`, {
			headers: authHeaders(token)
		});
	}
	for (const id of createdFolderIds) {
		await page.request.delete(`${BACKEND_API_URL}/folders/${id}/`, {
			headers: authHeaders(token)
		});
	}
});
