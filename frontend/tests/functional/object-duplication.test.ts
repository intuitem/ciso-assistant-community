import { test as testV2, expect as expectV2 } from '../utilsv2/core/base';

import type { ListViewPage } from '../utilsv2/base/list-view-page';
import type { Page } from '../utilsv2/core/page';
import type { Element } from '../utilsv2/core/element';

import { LoginPage } from '../utilsv2/derived/login-page';
import { ADMIN_EMAIL, ADMIN_PASSWORD } from '../utilsv2/core/test-data';

import {
	LibraryListViewPage,
	AppliedControlListViewPage,
	RiskAssessmentListViewPage,
	FolderListViewPage,
	PerimeterListViewPage
} from '../utilsv2/derived/list-view';
import {
	AppliedControlCreateModal,
	RiskAssessmentCreateModal
} from '../utilsv2/derived/create-modal';
import type { CreateModal } from '../utilsv2/base/create-modal';
import { safeTranslate } from '$lib/utils/i18n';

const DOMAIN_NAME = 'Object-Duplication domain';
const PERIMETER_NAME = 'Object-Duplication perimeter';
const RISK_MATRIX_NAME = 'critical_3x3';

interface LocalTestData {
	pageClass: Page.Class<ListViewPage>;
	modalClass: Element.Class<CreateModal>;
	objectName: string;
	formData: { [key: string]: any };
}

const TEST_DATA: LocalTestData[] = [
	{
		pageClass: AppliedControlListViewPage,
		modalClass: AppliedControlCreateModal,
		objectName: 'Applied control',
		formData: {
			name: 'Object-Duplication Applied control',
			foder: DOMAIN_NAME
		}
	},
	{
		pageClass: RiskAssessmentListViewPage,
		modalClass: RiskAssessmentCreateModal,
		objectName: 'Risk assessment',
		formData: {
			name: 'Object-Duplication Risk assessment',
			perimeter: PERIMETER_NAME,
			risk_matrix: RISK_MATRIX_NAME
		}
	}
];

testV2('object duplication is working properly', async ({ page }) => {
	testV2.slow();

	const loginPage = new LoginPage(page);
	await loginPage.gotoSelf();
	await loginPage.waitUntilLoaded();

	const analyticsPage = await loginPage.doLoginP(ADMIN_EMAIL, ADMIN_PASSWORD);
	await analyticsPage.waitUntilLoaded();
	await analyticsPage.checkSelf(expectV2);
	await analyticsPage.doCloseModal();

	const libraryListView = new LibraryListViewPage(page);
	await libraryListView.gotoSelf();
	const modelTable = libraryListView.getModelTable();

	await testV2.step('Loading risk matrix for risk assessment creation', async () => {
		await modelTable.checkIfSearchBarVisible(expectV2);
		await modelTable.doSearch(RISK_MATRIX_NAME);
		await modelTable.checkDisplayedRowCount(expectV2, 1);

		const firstRow = modelTable.getFirstRow();
		await firstRow.checkValue(expectV2, 1, RISK_MATRIX_NAME);
		const libraryCount = await libraryListView.getLoadedLibraryCount();
		await firstRow.doLoadLibrary();
		const toast = libraryListView.getToast();
		await toast.checkIfVisible(expectV2);
		await toast.checkContainText(expectV2, safeTranslate('librarySuccessfullyLoaded'));

		await libraryListView.checkLoadedLibraryCount(expectV2, libraryCount + 1);
	});

	await testV2.step('Creating domain to allow perimeter creation', async () => {
		const folderListView = new FolderListViewPage(page);
		await folderListView.gotoSelf();
		const folderCreateModal = await folderListView.getOpenCreateModal();
		const folderForm = folderCreateModal.getForm();
		await folderForm.doFillForm({
			name: DOMAIN_NAME
		});
		await folderForm.doSubmit();
	});

	await testV2.step('Creating perimeter to allow risk assessment creation', async () => {
		const perimeterListView = new PerimeterListViewPage(page);
		await perimeterListView.gotoSelf();
		const folderCreateModal = await perimeterListView.getOpenCreateModal();
		const perimeterForm = folderCreateModal.getForm();
		await perimeterForm.doFillForm({
			name: PERIMETER_NAME,
			folder: DOMAIN_NAME
		});
		await perimeterForm.doSubmit();
	});

	// Put this logic in a for loop.
	for (const testData of TEST_DATA) {
		await testV2.step(`The ${testData.objectName} can be duplicated`, async () => {
			const listView = new testData.pageClass(page);
			await listView.gotoSelf();

			const createModal = await listView.getOpenCreateModal();
			const createForm = createModal.getForm();
			const formData = structuredClone(testData.formData);
			await createForm.doFillForm(formData);
			await createForm.doSubmit();

			await listView.gotoSelf();

			const modelTable = listView.getModelTable();
			// Create an element fist
			await modelTable.doSearch(formData.name);
			await modelTable.checkDisplayedRowCount(expectV2, 1);

			const firstRow = modelTable.getFirstRow();
			const detailView = await firstRow.gotoDetailView(expectV2);
			const duplicateModal = await detailView.getOpenDuplicateModal(testData.modalClass);
			const duplicateForm = duplicateModal.getForm();

			formData.name += '_duplicated';
			await duplicateForm.doFillForm(formData);
			await duplicateForm.doSubmit();

			await listView.gotoSelf();
			// await appliedControlListView.waitUntilLoaded();
			await modelTable.doSearch(formData.name);
			await modelTable.checkDisplayedRowCount(expectV2, 1);
		});
	}
});
