import { defineConfig, devices } from '@playwright/test';

/**
 * Screenshot harness for product-docs. Deliberately separate from
 * `playwright.config.ts`: this project captures on success, writes into
 * `product-docs/.gitbook/assets/`, and must stay single-worker and
 * deterministic. It assumes the demo stack is already up — see
 * `tests/docs-screenshots/README.md`.
 */
const BASE_URL = process.env.DOCS_SHOTS_BASE_URL ?? 'http://localhost:5273';

const VIEWPORT = {
	viewport: { width: 1440, height: 900 },
	deviceScaleFactor: Number(process.env.DOCS_SHOTS_DSF ?? 1)
};

export default defineConfig({
	testDir: 'tests/docs-screenshots',
	outputDir: 'tests/docs-screenshots/.results',
	fullyParallel: false,
	workers: 1,
	retries: 0,
	timeout: 90 * 1000,
	reporter: [['list']],
	use: {
		baseURL: BASE_URL,
		locale: 'en-GB',
		timezoneId: 'UTC',
		colorScheme: 'light',
		...VIEWPORT,
		screenshot: 'off',
		video: 'off',
		trace: 'off'
	},
	projects: [
		{
			name: 'setup',
			testMatch: /auth\.setup\.ts/,
			use: { ...devices['Desktop Chrome'], ...VIEWPORT }
		},
		{
			name: 'shots',
			testMatch: /capture\.spec\.ts/,
			dependencies: ['setup'],
			use: {
				...devices['Desktop Chrome'],
				// Must come after the device spread — `devices` carries its own
				// viewport and would otherwise silently win.
				...VIEWPORT,
				storageState: 'tests/docs-screenshots/.auth/state.json'
			}
		}
	]
});
