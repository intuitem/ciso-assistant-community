import { enterpriseTest as enterpriseTestV2, expect as expectV2 } from '../../utilsv2/core/base';
import { LoginPage } from '../../utilsv2/derived/login-page';
import { LibraryListViewPage, QualificationListView } from '../../utilsv2/derived/list-view';

const LIBRARY_NAME = 'Qualification test library';
const QUALIFICATION_NAMES = ['Qualification 1', 'Qualification 2', 'Qualification 3'];

enterpriseTestV2('qualification import test', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.gotoSelf();
	const analyticsPage = await loginPage.doLoginAdminP();
	await analyticsPage.doCloseModal();

	const libraryListView = new LibraryListViewPage(page);
	await libraryListView.gotoSelf();
	await libraryListView.doUploadCustomLibrary(
		expectV2,
		'../../utils/qualification_test_library.yaml'
	);

	let modelTable = libraryListView.getModelTable();
	await modelTable.doSearch(LIBRARY_NAME);
	await modelTable.checkDisplayedRowCount(expectV2, 1);
	const storedLibraryRow = modelTable.getFirstRow();
	await storedLibraryRow.doLoadLibrary(expectV2);

	const qualificationListView = new QualificationListView(page);
	await qualificationListView.gotoSelf();
	modelTable = qualificationListView.getModelTable();
	for (const qualificationName of QUALIFICATION_NAMES) {
		await modelTable.doSearch(qualificationName);
		await modelTable.checkDisplayedRowCount(expectV2, 1);
	}
});
