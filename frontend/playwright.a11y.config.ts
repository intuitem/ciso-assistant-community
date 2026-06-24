import type { PlaywrightTestConfig } from '@playwright/test';
import { devices } from '@playwright/test';

// Accessibility audit config: drives an already-running dev server (default
// http://localhost:5173) instead of spawning a preview server. Override the
// target with A11Y_BASE_URL. The main playwright.config.ts is left untouched.
const config: PlaywrightTestConfig = {
	testDir: 'tests/functional',
	testMatch: 'accessibility.test.ts',
	globalSetup: './tests/a11y.global.ts',
	outputDir: 'tests/results',
	fullyParallel: false,
	workers: 1,
	retries: 0,
	timeout: 100 * 1000,
	expect: { timeout: 20 * 1000 },
	reporter: [['list'], ['html', { open: 'never', outputFolder: 'tests/reports/a11y-html' }]],
	use: {
		baseURL: process.env.A11Y_BASE_URL ?? 'http://localhost:5173',
		screenshot: 'only-on-failure',
		trace: 'retain-on-failure'
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
};

export default config;
