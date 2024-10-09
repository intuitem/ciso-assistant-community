import type { PlaywrightTestConfig } from '@playwright/test';
import { devices } from '@playwright/test';

const config: PlaywrightTestConfig = {
	webServer: {
		command: process.env.COMPOSE_TEST
			? 'echo "The docker compose frontend server didn\'t start correctly"'
			: 'pnpm run preview',
		port: process.env.COMPOSE_TEST ? 3000 : 4173,
		reuseExistingServer: !process.env.CI
	},
	testDir: 'tests',
	outputDir: 'tests/results',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 1,
	workers: process.env.CI ? 1 : 1,
	globalTimeout: 60 * 60 * 1000,
	timeout: 50 * 1000,
	expect: {
		timeout: 10 * 1000
	},
	reporter: [
		[process.env.CI ? 'github' : 'list'],
		[
			'html',
			{
				open: process.env.CI ? 'never' : process.env.DOCKER ? 'always' : 'on-failure',
				outputFolder: 'tests/reports',
				host: process.env.DOCKER ? '0.0.0.0' : 'localhost'
			}
		]
	],
	use: {
		screenshot: 'only-on-failure',
		video: process.env.CI ? 'retain-on-failure' : 'on',
		trace: process.env.CI ? 'retain-on-failure' : 'on',
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
		// 	name: 'webkit',
		// 	use: { ...devices['Desktop Safari'] },
		// }
	]
};

export default config;
