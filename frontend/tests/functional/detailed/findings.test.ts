import { test, TestContent } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('user can create asset assessments inside BIA', async ({
	page,
	pages,
	logedPage,
	foldersPage,
	perimetersPage,
	findingsAssessmentsPage
}) => {
	//NOTE: This is duplicated form business-impact-analysis.test.ts
	// It could be moved to a Fixture
	await test.step('create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.hasUrl();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
		// NOTE: creating one more folder not to trip up the autocomplete test utils
		await foldersPage.createItem({
			name: vars.folderName + ' foo',
			description: vars.description
		});
	});

	await test.step('create required perimeter', async () => {
		await perimetersPage.goto();
		await perimetersPage.hasUrl();
		await perimetersPage.createItem({
			name: vars.perimeterName,
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.1234',
			lc_status: 'Production'
		});
		await perimetersPage.createItem({
			name: vars.perimeterName + ' bar',
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.12345',
			lc_status: 'Production'
		});
	});

	await test.step('create findings assessment', async () => {
		await findingsAssessmentsPage.goto();
		await findingsAssessmentsPage.hasUrl();
		await findingsAssessmentsPage.createItem(testObjectsData.findingsAssessmentsPage.build);
	});

	await test.step('create findings inside', async () => {
		await findingsAssessmentsPage.viewItemDetail(
			testObjectsData.findingsAssessmentsPage.build.name
		);
		// await findingsAssessmentsPage.createItem({ asset: vars.assetName }, undefined, page);
	});
});
