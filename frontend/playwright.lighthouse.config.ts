import type { PlaywrightTestConfig } from '@playwright/test';
import { devices } from '@playwright/test';

// Lighthouse runs against the already-running dev server (default :5173) and needs
// Chromium launched with a remote-debugging port so it can attach via CDP.
const config: PlaywrightTestConfig = {
	testDir: 'tests/functional',
	testMatch: 'lighthouse.test.ts',
	outputDir: 'tests/results',
	fullyParallel: false,
	workers: 1,
	retries: 0,
	timeout: 120 * 1000,
	reporter: [['list']],
	use: {
		baseURL: process.env.A11Y_BASE_URL ?? 'http://localhost:5173',
		launchOptions: { args: ['--remote-debugging-port=9222'] }
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
};

export default config;
