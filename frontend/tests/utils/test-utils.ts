import { test as base, expect as baseExpect, type Page } from '@playwright/test';
import { SideBar } from './sidebar.js';
import { LoginPage } from './login-page.js';
import { AnalyticsPage } from './analytics-page.js';
import { PageContent } from './page-content.js';
import { FormFieldType as type } from './form-content.js';
import { Mailer } from './mailer.js';
import { randomBytes } from 'crypto';
import testData from './test-data.js';

type Fixtures = {
	data: { [key: string]: any };
	isolatedPage: Page;
	mailer: Mailer;
	sideBar: SideBar;
	pages: { [page: string]: PageContent };
	analyticsPage: AnalyticsPage;
	assetsPage: PageContent;
	complianceAssessmentsPage: PageContent;
	evidencesPage: PageContent;
	foldersPage: PageContent;
	frameworksPage: PageContent;
	librariesPage: PageContent;
	projectsPage: PageContent;
	riskAcceptancesPage: PageContent;
	riskAssessmentsPage: PageContent;
	riskMatricesPage: PageContent;
	riskScenariosPage: PageContent;
	referenceControlsPage: PageContent;
	appliedControlsPage: PageContent;
	threatsPage: PageContent;
	usersPage: PageContent;
	logedPage: LoginPage;
	loginPage: LoginPage;
	populateDatabase: void;
};

export const test = base.extend<Fixtures>({
	mailer: async ({ context }, use) => {
		const mailer = new Mailer(await context.newPage());
		await mailer.goto();
		await use(mailer);
	},

	sideBar: async ({ page }, use) => {
		await use(new SideBar(page));
	},

	isolatedPage: async ({ context }, use) => {
		await use(await context.newPage());
	},

	pages: async (
		{
			page,
			complianceAssessmentsPage,
			assetsPage,
			evidencesPage,
			foldersPage,
			frameworksPage,
			librariesPage,
			projectsPage,
			riskAcceptancesPage,
			riskAssessmentsPage,
			riskMatricesPage,
			riskScenariosPage,
			referenceControlsPage,
			appliedControlsPage,
			threatsPage,
			usersPage
		},
		use
	) => {
		await use({
			complianceAssessmentsPage,
			assetsPage,
			evidencesPage,
			foldersPage,
			frameworksPage,
			librariesPage,
			projectsPage,
			riskAcceptancesPage,
			riskAssessmentsPage,
			riskMatricesPage,
			riskScenariosPage,
			referenceControlsPage,
			appliedControlsPage,
			threatsPage,
			usersPage
		});
	},

	analyticsPage: async ({ page }, use) => {
		await use(new AnalyticsPage(page));
	},

	complianceAssessmentsPage: async ({ page }, use) => {
		const aPage = new PageContent(page, '/compliance-assessments', 'Audits', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'project', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'version', type: type.TEXT },
			{ name: 'status', type: type.SELECT },
			{ name: 'framework', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'eta', type: type.DATE },
			{ name: 'due_date', type: type.DATE }
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
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'link', type: type.TEXT }
		]);
		await use(ePage);
	},

	foldersPage: async ({ page }, use) => {
		const fPage = new PageContent(page, '/folders', 'Domains');
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
			{ name: 'lc_status', type: type.SELECT }
		]);
		await use(pPage);
	},

	riskAcceptancesPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-acceptances', 'Risk acceptances', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'expiry_date', type: type.DATE },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'approver', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'risk_scenarios', type: type.SELECT_MULTIPLE_AUTOCOMPLETE }
		]);
		await use(rPage);
	},

	riskAssessmentsPage: async ({ page }, use) => {
		const rPage = new PageContent(page, '/risk-assessments', 'Risk assessments', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'project', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'version', type: type.TEXT },
			{ name: 'status', type: type.SELECT },
			{ name: 'risk_matrix', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'eta', type: type.DATE },
			{ name: 'due_date', type: type.DATE }
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
			{ name: 'risk_assessment', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'threats', type: type.SELECT_MULTIPLE_AUTOCOMPLETE },
			{ name: 'treatment', type: type.SELECT },
			{ name: 'assets', type: type.SELECT_MULTIPLE_AUTOCOMPLETE },
			{ name: 'existing_controls', type: type.TEXT },
			{ name: 'current_proba', type: type.SELECT },
			{ name: 'current_impact', type: type.SELECT },
			{ name: 'applied_controls', type: type.SELECT_MULTIPLE_AUTOCOMPLETE },
			{ name: 'residual_proba', type: type.SELECT },
			{ name: 'residual_impact', type: type.SELECT },
			{ name: 'justification', type: type.TEXT }
		]);
		await use(rPage);
	},

	referenceControlsPage: async ({ page }, use) => {
		const sPage = new PageContent(page, '/reference-controls', 'Reference controls', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'category', type: type.SELECT },
			{ name: 'csf_function', type: type.SELECT },
			{ name: 'provider', type: type.TEXT },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE }
		]);
		await use(sPage);
	},

	appliedControlsPage: async ({ page }, use) => {
		const sPage = new PageContent(page, '/applied-controls', 'Applied controls', [
			{ name: 'name', type: type.TEXT },
			{ name: 'description', type: type.TEXT },
			{ name: 'category', type: type.SELECT },
			{ name: 'csf_function', type: type.SELECT },
			{ name: 'status', type: type.SELECT },
			{ name: 'eta', type: type.DATE },
			{ name: 'expiry_date', type: type.DATE },
			{ name: 'link', type: type.TEXT },
			{ name: 'effort', type: type.SELECT },
			{ name: 'cost', type: type.NUMBER },
			{ name: 'folder', type: type.SELECT_AUTOCOMPLETE },
			{ name: 'reference_control', type: type.SELECT_AUTOCOMPLETE }
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

	usersPage: async ({ page }, use) => {
		const uPage = new PageContent(page, '/users', 'Users', [
			{ name: 'email', type: type.TEXT },
			{ name: 'first_name', type: type.TEXT },
			{ name: 'last_name', type: type.TEXT },
			{ name: 'user_groups', type: type.SELECT_MULTIPLE_AUTOCOMPLETE },
			{ name: 'is_active', type: type.CHECKBOX },
			{ name: 'new_password', type: type.TEXT },
			{ name: 'confirm_new_password', type: type.TEXT }
		]);
		await use(uPage);
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

	data: { ...testData },

	populateDatabase: async ({ pages, loginPage, sideBar, data }, use) => {
		test.slow();
		await loginPage.goto();
		await loginPage.login();
		for (const [page, pageData] of Object.entries(data)) {
			await pages[page].goto();
			await pages[page].waitUntilLoaded();
			await pages[page].createItem(
				pageData.build,
				'dependency' in pageData ? pageData.dependency : null
			);
		}
		await sideBar.logout();
		await use();
	}
});

export const expect = baseExpect.extend({
	toBeOneofValues(received: number, expected: number[]) {
		const pass = received >= expected[0] && received <= expected[1];
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
	},

	async toHaveTextUnordered(received: string[], expected: string[]) {
		const pass = expected.every((value) => received.includes(value));
		if (pass) {
			return {
				pass: true,
				message: () => `passed`
			};
		} else {
			return {
				pass: false,
				message: () => `expect(${received}).toHaveTextUnordered([${expected}])`
			};
		}
	}
});

export class TestContent {
	static itemBuilder(vars: { [key: string]: any } = this.generateTestVars()) {
		return {
			foldersPage: {
				displayName: 'Domains',
				build: {
					name: vars.folderName,
					description: vars.description
				},
				editParams: {
					name: '',
					description: ''
				}
			},
			usersPage: {
				displayName: 'Users',
				build: {
					email: vars.user.email
				},
				editParams: {
					email: '_' + vars.user.email,
					first_name: vars.user.firstName,
					last_name: vars.user.lastName,
					user_groups: [
						`${vars.folderName} - ${vars.usergroups.analyst.name}`,
						`${vars.folderName} - ${vars.usergroups.reader.name}`,
						`${vars.folderName} - ${vars.usergroups.domainManager.name}`,
						`${vars.folderName} - ${vars.usergroups.approver.name}`
					],
					is_active: false
				}
			},
			projectsPage: {
				displayName: 'Projects',
				build: {
					name: vars.projectName,
					description: vars.description,
					folder: vars.folderName,
					internal_reference: 'Test internal reference',
					lc_status: 'Production'
				},
				editParams: {
					name: '',
					description: '',
					internal_reference: '',
					lc_status: 'End of life'
				}
			},
			assetsPage: {
				displayName: 'Assets',
				build: {
					name: vars.assetName,
					description: vars.description,
					business_value: 'Test value',
					folder: vars.folderName,
					type: 'Primary'
				},
				editParams: {
					name: '',
					description: '',
					business_value: '',
					type: 'Supporting'
					//TODO add parent_assets
				}
			},
			threatsPage: {
				displayName: 'Threats',
				build: {
					name: vars.threatName,
					description: vars.description,
					folder: vars.folderName,
					provider: 'Test provider'
				},
				editParams: {
					name: '',
					description: '',
					provider: ''
				}
			},
			referenceControlsPage: {
				displayName: 'Reference controls',
				build: {
					name: vars.referenceControlName,
					description: vars.description,
					category: 'Technical',
					csf_function: 'protect',
					provider: 'Test provider',
					folder: vars.folderName
				},
				editParams: {
					name: '',
					description: '',
					category: 'Physical',
					csf_function: 'detect',
					provider: ''
				}
			},
			appliedControlsPage: {
				displayName: 'Applied controls',
				dependency: vars.referenceControl.library,
				build: {
					reference_control: {
						value: 'Global/' + vars.referenceControl.name,
						category: vars.referenceControl.category,
						csf_function: vars.referenceControl.csf_function,
						request: {
							url: 'reference-controls'
						}
					},
					name: vars.appliedControlName,
					description: vars.description,
					status: 'To do',
					eta: '2025-01-01',
					expiry_date: '2025-05-01',
					link: 'https://intuitem.com/',
					effort: 'Large',
					folder: vars.folderName,
					category: vars.referenceControl.category,
					csf_function: vars.referenceControl.csf_function
				},
				editParams: {
					reference_control: {
						value: 'Global/' + vars.referenceControl2.name,
						category: vars.referenceControl2.category,
						csf_function: vars.referenceControl2.csf_function,
						request: {
							url: 'reference-controls'
						}
					},
					name: '',
					description: '',
					status: 'Active',
					eta: '2025-12-31',
					expiry_date: '2026-02-25',
					link: 'https://intuitem.com/community/',
					effort: 'Medium',
					category: vars.referenceControl2.category,
					csf_function: vars.referenceControl2.csf_function
				}
			},
			complianceAssessmentsPage: {
				displayName: 'Audits',
				permName: 'complianceassessment',
				dependency: vars.framework,
				build: {
					name: vars.assessmentName,
					description: vars.description,
					project: vars.folderName + '/' + vars.projectName,
					status: 'Planned',
					// version: "1.4.2",
					framework: vars.framework.name
					// eta: "2025-01-01",
					// due_date: "2025-05-01"
				},
				editParams: {
					name: '',
					description: ''
					// version: "1.4.3",
					//TODO add framework
					// eta: "2025-12-31",
					// due_date: "2026-02-25"
				}
			},
			evidencesPage: {
				displayName: 'Evidences',
				dependency: vars.framework,
				build: {
					name: vars.evidenceName,
					description: vars.description,
					attachment: vars.file,
					folder: vars.folderName,
					requirement_assessments: [
						vars.requirement_assessment.name,
						vars.requirement_assessment2.name
					],
					link: 'https://intuitem.com/'
				},
				editParams: {
					name: '',
					description: '',
					attachment: vars.file2,
					link: 'https://intuitem.com/community/'
				}
			},
			riskAssessmentsPage: {
				displayName: 'Risk assessments',
				dependency: vars.matrix,
				build: {
					name: vars.riskAssessmentName,
					description: vars.description,
					project: vars.folderName + '/' + vars.projectName,
					version: vars.riskAssessmentVersion,
					status: 'Planned',
					risk_matrix: vars.matrix.displayName
					// eta: "2025-01-01",
					// due_date: "2025-05-01"
				},
				editParams: {
					name: '',
					description: '',
					version: vars.riskAssessmentVersion2
					//TODO add risk_matrix
					// eta: "2025-12-31",
					// due_date: "2026-02-25"
				}
			},
			riskScenariosPage: {
				displayName: 'Risk scenarios',
				dependency: vars.threat.library,
				build: {
					name: vars.riskScenarioName,
					description: vars.description,
					risk_assessment: `${vars.folderName}/${vars.projectName}/${vars.riskAssessmentName} - ${vars.riskAssessmentVersion}`,
					threats: ['Global/' + vars.threat.name, 'Global/' + vars.threat2.name]
				},
				editParams: {
					name: '',
					description: '',
					treatment: 'Accepted',
					//TODO add risk_assessment & threats
					assets: [vars.folderName + '/' + vars.assetName],
					existing_controls: 'Test Existing Controls',
					current_proba: 'High',
					current_impact: 'Medium',
					applied_controls: [vars.folderName + '/' + vars.appliedControlName],
					residual_proba: 'Medium',
					residual_impact: 'Low',
					justification: 'Test comments'
				}
			},
			riskAcceptancesPage: {
				displayName: 'Risk acceptances',
				build: {
					name: vars.riskAcceptanceName,
					description: vars.description,
					expiry_date: '2025-01-01',
					folder: vars.folderName,
					approver: LoginPage.defaultEmail,
					risk_scenarios: [
						`${vars.folderName}/${vars.projectName}/${vars.riskAssessmentName} - ${vars.riskAssessmentVersion}/${vars.riskScenarioName}`
					]
				},
				editParams: {
					name: '',
					description: '',
					expiry_date: '2025-12-31'
					//TODO add approver & risk_scenarios
				}
			}
		};
	}

	static generateTestVars(data = testData) {
		const vars = structuredClone(data);
		for (const key in data) {
			if (typeof data[key] === 'object') {
				if ('email' in data[key]) {
					vars[key] = this.generateTestVars(data[key]);
				}
			} else if (key.match(/.*Name/) || vars[key].match(/.+@.+/)) {
				vars[key] = getUniqueValue(data[key]);
			}
		}
		return vars;
	}
}

export function setHttpResponsesListener(page: Page) {
	page.on('response', (response) => {
		expect.soft(response.status()).toBeOneofValues([100, 399]);
	});
}

export function getSingularName(pluralName: string) {
	const exceptions: any = {
		Domains: 'Folder',
		Libraries: 'Library',
		'Risk matrices': 'Risk matrix',
		Policies: 'Policy'
	};
	return (
		exceptions[pluralName] ??
		(pluralName.endsWith('s') ? pluralName.substring(0, pluralName.length - 1) : pluralName)
	);
}

export function getUniqueValue(value: string): string {
	if (value.match(/.+@.+/)) {
		const email = value.split('@');
		return getUniqueValue(email[0]) + '@' + email[1];
	}
	return process.env.TEST_WORKER_INDEX + '-' + value + '-' + randomBytes(2).toString('hex');
}

export function replaceValues(obj: any, searchValue: string, replaceValue: string) {
	for (const key in obj) {
		if (typeof obj[key] === 'object') {
			replaceValues(obj[key], searchValue, replaceValue);
		} else if (typeof obj[key] === 'string') {
			obj[key] = obj[key].replace(searchValue, replaceValue);
		}
	}
}

export function userFromUserGroupHasPermission(
	userGroup: string,
	permission: string,
	object: string
) {
	const perm = `${permission}_${getSingularName(object).toLowerCase().replace(' ', '')}`;
	return userGroup in testData.usergroups && testData.usergroups[userGroup].perms.includes(perm);
}

export function getObjectNameWithoutScope(name: string) {
	const scopeList = name.split('/');
	return scopeList[scopeList.length - 1];
}

export { test as baseTest, type Page, type Locator } from '@playwright/test';
