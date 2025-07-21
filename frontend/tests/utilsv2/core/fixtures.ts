import type { Page as _Page } from '@playwright/test';
import { LoginPage } from '../derived/login-page';

export interface Fixtures extends AllFixtures {
	/** Contain all fixtures as a dictionary */
	page: _Page;
	allFixtures: Fixtures;
}

export interface AllFixtures {
	page: _Page;
	loginPage: LoginPage;
}

export const fixtures = {
	loginPage: async ({ page }, use) => {
		await use(new LoginPage(page));
	},

	allFixtures: async ({ page, loginPage }, use) => {
		use({
			page,
			loginPage
		});
	}
};
