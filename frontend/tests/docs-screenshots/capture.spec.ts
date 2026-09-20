import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { annotate } from './annotate.js';
import { shots } from './manifest.js';

const ASSETS = path.resolve('../product-docs/.gitbook/assets');

/** Kill motion and caret blink so two runs of the same page are pixel-identical. */
const FREEZE = `
	*, *::before, *::after {
		animation-duration: 0s !important;
		animation-delay: 0s !important;
		transition-duration: 0s !important;
		transition-delay: 0s !important;
		caret-color: transparent !important;
	}
	.animate-pulse, .animate-spin { animation: none !important; }
`;

test.describe('documentation screenshots', () => {
	test.beforeAll(async () => {
		await mkdir(ASSETS, { recursive: true });
	});

	for (const shot of shots) {
		test(shot.slug, async ({ page }) => {
			await page.goto(shot.url);
			await page.locator('body[data-hydrated="true"]').waitFor();
			await shot.then?.(page);

			// Let tables, charts and lazy autocompletes settle before freezing the page.
			await page.waitForLoadState('networkidle');
			await page.addStyleTag({ content: FREEZE });
			// Some detail routes nest a second <main>; the outer one is enough.
			await expect(page.locator('main').first()).toBeVisible();

			if (shot.annotate) {
				await annotate(page, shot.annotate(page));
			}

			const target = shot.clip ? shot.clip(page) : page;
			await target.screenshot({
				path: path.join(ASSETS, `${shot.slug}.png`),
				animations: 'disabled',
				scale: process.env.DOCS_SHOTS_SCALE === 'device' ? 'device' : 'css',
				...(shot.clip ? {} : { fullPage: shot.fullPage ?? false })
			});
		});
	}
});
