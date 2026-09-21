import { expect, test, type Page } from '../utils/test-utils.js';

/**
 * `/service-accounts` is the one page the Enterprise sidebar lists that the palette also
 * carries as an extra destination of its own — and only once this flag is on. Two navigation
 * commands then share an href, Svelte throws `each_key_duplicate` as the result list renders,
 * and the palette comes up empty. Community has no sidebar entry for the page, so it never
 * collides; that is the whole reason this has to be switched on before the palette is opened.
 *
 * Returns what the flag was, or null where this edition does not offer it.
 */
async function setServiceAccounts(page: Page, enabled: boolean): Promise<boolean | null> {
	await page.goto('/settings');
	await page.waitForLoadState('networkidle');

	const tab = page.getByRole('tab', { name: /feature flags/i });
	await expect(tab).toBeVisible();
	await tab.click();

	const card = page
		.locator('[role="checkbox"]')
		.filter({ has: page.locator('span.font-semibold', { hasText: 'Service accounts' }) });
	// An edition that does not offer the flag cannot produce the collision.
	if ((await card.count()) === 0) return null;

	const was = (await card.getAttribute('aria-checked')) === 'true';
	if (was !== enabled) {
		await card.click();
		await expect(card).toHaveAttribute('aria-checked', String(enabled));
		await page.getByRole('button', { name: /save/i }).click();
		await expect(page.getByTestId('toast')).toBeVisible();
	}
	return was;
}

/** Null until the flag has actually been changed, so a failure before that restores nothing. */
let previousServiceAccounts: boolean | null = null;

// The flag is global state and the suite shares one backend, so put it back. This is a hook
// rather than a `finally`: a throwing `finally` would replace the assertion error that failed
// the test, while Playwright reports a failing hook alongside it — and still runs it on failure.
test.afterEach(async ({ page }) => {
	if (previousServiceAccounts === null) return;
	const restore = previousServiceAccounts;
	previousServiceAccounts = null;
	await setServiceAccounts(page, restore);
});

test('command palette opens and lists commands', async ({ logedPage, page }) => {
	// A keyed-`{#each}` collision is the one crash that leaves the palette looking merely
	// empty, so watch for it by name rather than trusting the emptiness check alone.
	const keyErrors: string[] = [];
	page.on('pageerror', (error) => {
		if (error.message.includes('each_key_duplicate')) keyErrors.push(error.message);
	});

	const palette = page.getByTestId('command-palette');
	const results = palette.locator('[data-cmdk-index]');

	await test.step('put the sidebar in the shape that collides', async () => {
		// Also asserts we landed on /analytics with no modal left to swallow the keypress.
		await logedPage.skipWelcome();
		previousServiceAccounts = await setServiceAccounts(page, true);
		// The layout reads the flags server-side, so the palette needs a fresh load to see it.
		await page.goto('/analytics');
		await page.waitForLoadState('networkidle');
	});

	await test.step('the keyboard shortcut opens it', async () => {
		await page.keyboard.press('ControlOrMeta+k');
		await expect(palette).toBeVisible();
	});

	await test.step('it lists navigation commands', async () => {
		await expect(results.first()).toBeVisible();
		expect(await results.count()).toBeGreaterThan(1);
	});

	await test.step('typing filters the list down', async () => {
		await palette.getByRole('textbox').fill('asset');
		await expect(results.first()).toBeVisible();
		await expect(results.first()).toContainText(/asset/i);
	});

	await test.step('escape closes it', async () => {
		await page.keyboard.press('Escape');
		await expect(palette).toBeHidden();
	});

	await test.step('the appbar button opens it too', async () => {
		await page.getByTestId('command-palette-trigger').click();
		await expect(palette).toBeVisible();
		await expect(results.first()).toBeVisible();
	});

	await test.step('the + sigil switches to create mode', async () => {
		await palette.getByRole('textbox').fill('+');
		await expect(results.first()).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(palette).toBeHidden();
	});

	expect(keyErrors, `the palette raised: ${keyErrors.join(' | ')}`).toEqual([]);
});
