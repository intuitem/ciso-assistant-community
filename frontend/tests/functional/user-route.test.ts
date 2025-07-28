import { test as testV2, expect as expectV2 } from '../utilsv2/core/base';

import type { ListViewPage } from '../utilsv2/base/list-view-page';
import type { Page } from '../utilsv2/core/page';

import { LoginPage } from '../utilsv2/derived/login-page';
import { LibraryListViewPage } from '../utilsv2/derived/list-view';
import { safeTranslate } from '$lib/utils/i18n';
import { ADMIN_EMAIL, ADMIN_PASSWORD } from '../utilsv2/core/test-data';

import {
	FolderListViewPage,
	PerimeterListViewPage,
	AssetListViewPage,
	AppliedControlListViewPage,
	ExceptionListViewPage,
	ComplianceAssessmentListViewPage,
	EvidenceListViewPage,
	RiskAssessmentListViewPage,
	ThreatListViewPage,
	RiskScenarioListViewPage,
	RiskAcceptanceListViewPage,
	UserListViewPage
} from '../utilsv2/derived/list-view';

interface LocalTestData {
	pageClass: Page.Class<ListViewPage>;
	objectName: string;
	formData: { [key: string]: any };
}
const TEST_DATA: LocalTestData[] = [
	{
		pageClass: FolderListViewPage,
		objectName: 'Domain',
		formData: {
			name: 'User-Routes Domain',
			description: 'This is the user-routes domain.'
		}
	},
	{
		pageClass: PerimeterListViewPage,
		objectName: 'Perimeter',
		formData: {
			name: 'User-Routes Perimeter',
			description: 'This is the user-routes perimeter.'
		}
	},
	{
		pageClass: AssetListViewPage,
		objectName: 'Asset',
		formData: {
			name: 'User-Routes Asset',
			description: 'This is a user-routes asset.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: AppliedControlListViewPage,
		objectName: 'Applied Control',
		formData: {
			name: 'User-Routes Applied Control',
			description: 'This is the user-routes applied control.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: ExceptionListViewPage,
		objectName: 'Security Exception',
		formData: {
			name: 'User-Routes Exception',
			description: 'This is the user-routes exception.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: ComplianceAssessmentListViewPage,
		objectName: 'Audit',
		formData: {
			name: 'User-Routes Audit',
			description: 'This is the user-routes audit.'
		}
	},
	{
		pageClass: EvidenceListViewPage,
		objectName: 'Evidence',
		formData: {
			name: 'User-Routes Evidence',
			description: 'This is the user-routes evidence.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: RiskAssessmentListViewPage,
		objectName: 'Risk Assessment',
		formData: {
			name: 'User-Routes Risk Assessment',
			description: 'This is the user-routes risk assessment.'
		}
	},
	{
		pageClass: ThreatListViewPage,
		objectName: 'Threat',
		formData: {
			name: 'User-Routes Threat',
			description: 'This is the user-routes threat.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: RiskScenarioListViewPage,
		objectName: 'Risk scenario',
		formData: {
			name: 'User-Routes Risk scenario',
			description: 'This is the user-routes risk scenario.',
			folder: 'User-Routes Domain'
		}
	},
	{
		pageClass: RiskAcceptanceListViewPage,
		objectName: 'Risk acceptance',
		formData: {
			name: 'User-Routes Risk acceptance',
			description: 'This is the user-routes risk acceptance.',
			riskScenarios: 'User-Routes Risk scenario'
		}
	},
	{
		pageClass: UserListViewPage,
		objectName: 'User',
		formData: {
			email: 'user-routes@tests.com'
		}
	}
];

testV2('user usual routine actions are working correctly', async ({ page }) => {
	testV2.slow();

	const loginPage = new LoginPage(page);
	await loginPage.gotoSelf();
	await loginPage.waitUntilLoaded();

	const analyticsPage = await loginPage.doLoginP(ADMIN_EMAIL, ADMIN_PASSWORD);
	await analyticsPage.waitUntilLoaded();
	await analyticsPage.checkSelf(expectV2);
	await analyticsPage.doCloseModal(); // Closes the FirstLoginModal component.

	const libraryListView = new LibraryListViewPage(page);
	await libraryListView.gotoSelf();
	const modelTable = libraryListView.getModelTable();

	await testV2.step('User can load a framework', async () => {
		await modelTable.checkIfSearchBarVisible(expectV2);
		await modelTable.doSearch('anssi-architectures-si-sensibles-dr');
		await modelTable.checkDisplayedRowCount(expectV2, 1);

		let firstRow = modelTable.getFirstRow();
		await firstRow.checkValue(expectV2, 1, 'anssi-architectures-si-sensibles-dr');
		const libraryCount = await libraryListView.getLoadedLibraryCount();
		await firstRow.doLoadLibrary(true);
		const toast = libraryListView.getToast();
		await toast.checkIfVisible(expectV2);
		await toast.checkContainText(expectV2, safeTranslate('librarySuccessfullyLoaded'));

		await libraryListView.checkLoadedLibraryCount(expectV2, libraryCount + 1);
	});

	await testV2.step('User can load a risk matrix', async () => {
		await modelTable.doSearch('critical_5x5');
		await modelTable.checkDisplayedRowCount(expectV2, 1);

		const firstRow = modelTable.getFirstRow();
		await firstRow.checkValue(expectV2, 1, 'critical_5x5');
		const libraryCount = await libraryListView.getLoadedLibraryCount();
		await firstRow.doLoadLibrary(true);
		const toast = libraryListView.getToast();
		await toast.checkIfVisible(expectV2);
		await toast.checkContainText(expectV2, safeTranslate('librarySuccessfullyLoaded'));

		await libraryListView.checkLoadedLibraryCount(expectV2, libraryCount + 1);
	});

	for (const testData of TEST_DATA) {
		await testV2.step(`User can create a ${testData.objectName}`, async () => {
			const listView = new testData.pageClass(page);
			await listView.gotoSelf();

			const createModal = await listView.getOpenCreateModal();
			const createForm = createModal.getForm();
			await createForm.doFillForm(testData.formData);
			await createForm.doSubmit();

			const toast = listView.getToast();
			await toast.checkIfVisible(expectV2);
			await toast.checkContainText(expectV2, 'object has been successfully created');

			const modelTable = listView.getModelTable();
			await modelTable.doSearch(testData.formData.name ?? testData.formData.email);
			await modelTable.checkDisplayedRowCount(expectV2, 1);

			const firstRow = modelTable.getFirstRow();
			await firstRow.checkIfVisible(expectV2);

			await listView.waitUntilLoaded();
		});
	}

	for (const testData of TEST_DATA.slice().reverse()) {
		await testV2.step(`User can delete a ${testData.objectName}`, async () => {
			const listView = new testData.pageClass(page);
			await listView.gotoSelf();

			const modelTable = listView.getModelTable();
			await modelTable.doSearch(testData.formData.name ?? testData.formData.email);
			await modelTable.checkDisplayedRowCount(expectV2, 1);

			const firstRow = modelTable.getFirstRow();
			await firstRow.checkIfVisible(expectV2);
			await firstRow.doDeleteObject();

			const toast = listView.getToast();
			await toast.checkContainText(expectV2, 'object has been successfully deleted');
			await modelTable.checkDisplayedRowCount(expectV2, 0);
		});
	}
});
