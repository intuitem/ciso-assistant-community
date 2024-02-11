import type { PlaywrightTestConfig } from '@playwright/test';
import { devices } from '@playwright/test';

const config: PlaywrightTestConfig = {
	webServer: {
		command: 'npm run build && npm run preview',
		port: 4173
	},
	testDir: 'tests',
	outputDir: 'tests/results',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 1,
	workers: process.env.CI ? 2 : 2,
	globalTimeout: 60 * 60 * 1000,
	timeout: 60 * 1000,
	reporter: [
		[process.env.CI ? 'github' : 'list'],
		['html', { open: 'never', outputFolder: 'tests/reports' }]
	],
	use: {
		// launchOptions: {
		// 	slowMo: 1000,
		// },
		screenshot: 'only-on-failure',
		video: 'retain-on-failure',
		trace: 'retain-on-failure',
		contextOptions: {
			recordVideo: { dir: 'tests/results/videos' }
		}
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		},
		{
			name: 'firefox',
			use: { ...devices['Desktop Firefox'] }
		}
		// {
		// 	name: 'webkit',
		// 	use: { ...devices['Desktop Safari'] },
		// }
	]
};

export default config;
