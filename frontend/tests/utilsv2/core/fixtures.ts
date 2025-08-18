import type { Page as _Page } from '@playwright/test';
import { LoginPage } from '../derived/login-page';
import { AuditLogPage } from '../derived/audit-log-page';

export interface Fixtures extends AllFixtures {
	page: _Page;
	/** Contain all fixtures as a dictionary */
	allFixtures: Fixtures;
}

export interface AllFixtures {
	page: _Page;
	loginPage: LoginPage;
	auditLogPage: AuditLogPage;
}

type FixtureType = {
	[key: string]: (fixtures: AllFixtures, use: (fixture: any) => void) => Promise<any>;
};

export const fixtures: FixtureType = {
	loginPage: async ({ page }, use) => {
		const fixture = new LoginPage(page);
		await use(fixture);
	},
	auditLogPage: async ({ page }, use) => {
		const fixture = new AuditLogPage(page);
		await use(fixture);
	},

	allFixtures: async ({ page, loginPage, auditLogPage }, use) => {
		use({
			page,
			loginPage,
			auditLogPage
		});
	}
};
