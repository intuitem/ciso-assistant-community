import { test as base, expect as baseExpect, type Page } from '@playwright/test';
import { SideBar } from './sidebar';
import { Layout } from './layout';
import { LoginPage } from './login-page';
import { AnalyticsPage } from './analytics-page';
import { PageContent } from './page-content';
import { FormFieldType as type } from './form-content';

type Fixtures = {
	layout: Layout;
	sideBar: SideBar;
	pages: { [page: string]: PageContent };
	assessmentsPage: PageContent;
	assetsPage: PageContent;
	evidencesPage: PageContent;
	foldersPage: PageContent;
	frameworksPage: PageContent;
	librariesPage: PageContent;
	projectsPage: PageContent;
	riskAcceptancesPage: PageContent;
	riskAnalysesPage: PageContent;
	riskMatricesPage: PageContent;
	riskScenariosPage: PageContent;
	securityFunctionsPage: PageContent;
	securityMeasuresPage: PageContent;
	threatsPage: PageContent;
	analyticsPage: AnalyticsPage;
	logedPage: LoginPage;
	loginPage: LoginPage;
};

export const test = base.extend<Fixtures>({
	layout: async ({ logedPage }, use) => {
		await use(new Layout(logedPage.page));
	},

	sideBar: async ({ page }, use) => {
		await use(new SideBar(page));
	},

	pages: async (
		{
			page,
			assessmentsPage,
			assetsPage,
			evidencesPage,
			foldersPage,
			frameworksPage,
			librariesPage,
			projectsPage,
			riskAcceptancesPage,
			riskAnalysesPage,
			riskMatricesPage,
			riskScenariosPage,
			securityFunctionsPage,
			securityMeasuresPage,
			threatsPage
		},
		use
	) => {
		await use({
			assessmentsPage,
			assetsPage,
			evidencesPage,
			foldersPage,
			frameworksPage,
			librariesPage,
			projectsPage,
			riskAcceptancesPage,
			riskAnalysesPage,
			riskMatricesPage,
			riskScenariosPage,
			securityFunctionsPage,
			securityMeasuresPage,
			threatsPage
		});
	},

	assessmentsPage: async ({ page }, use) => {
		const aPage = new PageContent(page, '/assessments', 'Assessments', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'project', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'framework', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'version', type: type.TEXT },
			{ name: 'is_draft', type: type.CHECKBOX },
			{ name: 'is_obsolete', type: type.CHECKBOX }
		]);
		await use(aPage);
	},

	assetsPage: async ({ page }, use) => {
		const aPage = new PageContent(page, '/assets', 'Assets', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'business_value', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'type', type: type.SELECT },
			{ name: 'parent_assets', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(aPage);
	},

	evidencesPage: async ({ page }, use) => {
		const ePage = new PageContent(page, '/evidences', 'Evidences', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'attachment', type: type.FILE },
			{ name: 'security_measure', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'comment', type: type.TEXT }
		]);
		await use(ePage);
	},

	foldersPage: async ({ page }, use) => {
		const fPage = new PageContent(page, '/folders', 'Domains');
		fPage.form.name = 'New Folder';
		await use(fPage);
	},

	frameworksPage: async ({ page }, use) => {
		const fPage = new PageContent(page, '/frameworks', 'Frameworks');
		await use(fPage);
	},

	librariesPage: async ({ page }, use) => {
		const lPage = new PageContent(page, '/libraries', 'Libraries');
		await use(lPage);
	},

	projectsPage: async ({ page }, use) => {
		const pPage = new PageContent(page, '/projects', 'Projects', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'internal_reference', type: type.TEXT },
			{ name: 'lc_status', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(pPage);
	},

	riskAcceptancesPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-acceptances', 'Risk acceptances', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'expiry_date', type: type.TEXT },
			{ name: 'justification', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'approver', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'risk_scenarios', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(rPage);
	},

	riskAnalysesPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-analyses', /Risk analys[ie]s/, [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'project', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'version', type: type.TEXT },
			{ name: 'is_draft', type: type.CHECKBOX },
			{ name: 'auditor', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'risk_matrix', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(rPage);
	},

	riskMatricesPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-matrices', 'Risk matrices');
		await use(rPage);
	},

	riskScenariosPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-scenarios', 'Risk scenarios', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'analysis', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'threat', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(rPage);
	},

	securityFunctionsPage: async ({ page }, use) => {
		const sPage = new PageContent(page, '/security-functions', 'Security functions', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'provider', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(sPage);
	},

	securityMeasuresPage: async ({ page }, use) => {
		const sPage = new PageContent(page, '/security-measures', 'Security measures', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'type', type: type.SELECT },
			{ name: 'status', type: type.SELECT },
			{ name: 'eta', type: type.TEXT },
			{ name: 'link', type: type.TEXT },
			{ name: 'effort', type: type.SELECT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'security_function', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(sPage);
	},

	threatsPage: async ({ page }, use) => {
		const tPage = new PageContent(page, '/threats', 'Threats', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'provider', type: type.TEXT }
		]);
		await use(tPage);
	},

	logedPage: async ({ page }, use) => {
		const loginPage = new LoginPage(page);
		await loginPage.goto();
		await loginPage.login();
		await use(loginPage);
	},

	loginPage: async ({ page }, use) => {
		await use(new LoginPage(page));
	},

	analyticsPage: async ({ page }, use) => {
		await use(new AnalyticsPage(page));
	}
});

export const expect = baseExpect.extend({
	toBeOneofValues(received: number, expected: number[]) {
		const pass = expected.includes(received);
		if (pass) {
			return {
				pass: true,
				message: () => `passed`
			};
		} else {
			return {
				pass: false,
				message: () => `expect(${received}).toBeOneofValues([${expected}])`
			};
		}
	},

	toBeOneofStrings(received: string, expected: string[]) {
		const pass = expected.includes(received);
		if (pass) {
			return {
				pass: true,
				message: () => `passed`
			};
		} else {
			return {
				pass: false,
				message: () => `expect(${received}).toBeOneofStrings([${expected}])`
			};
		}
	}
});

export function httpResponsesListener(page: Page) {
	page.on('response', (response) => {
		expect(
			response.status(),
			'An error with status code ' + response.status() + ' occured when trying to achieve operation'
		).toBeLessThan(400);
	});
	page.on('console', (message) => {
		expect(message.type()).not.toBe('error');
	});
}

export function getUniqueValue(value: string) {
	return process.env.TEST_WORKER_INDEX + '-' + value;
}

export { test as baseTest, type Page, type Locator } from '@playwright/test';
