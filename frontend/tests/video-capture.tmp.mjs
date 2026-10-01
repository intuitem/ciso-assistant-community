import { chromium } from '@playwright/test';

const BASE = 'http://localhost:5373';
const OUT = process.env.OUT;
const SHOTS = JSON.parse(process.env.SHOTS);

const browser = await chromium.launch();
const ctx = await browser.newContext({
	viewport: { width: 1600, height: 900 },
	deviceScaleFactor: 2,
	locale: 'en-US'
});
const page = await ctx.newPage();
await page.goto(`${BASE}/login`);
await page.locator('body[data-hydrated="true"]').waitFor();
await page.getByTestId('form-input-username').fill('admin@demo.local');
await page.getByTestId('form-input-password').fill('Demo1234!');
await page.getByTestId('login-btn').click();
await page.waitForURL((u) => !u.pathname.startsWith('/login'));

for (const s of SHOTS) {
	await page.goto(s.url.startsWith('http') ? s.url : `${BASE}${s.url}`);
	await page.waitForLoadState('networkidle').catch(() => {});
	if (s.click) {
		await page.getByText(s.click, { exact: false }).first().click();
		await page.waitForLoadState('networkidle').catch(() => {});
	}
	if (s.scroll) await page.mouse.wheel(0, s.scroll);
	await page.waitForTimeout(s.wait ?? 2500);
	await page.screenshot({ path: `${OUT}/${s.name}.png`, fullPage: !!s.full });
	console.log('shot', s.name);
}
await browser.close();
