import { test, TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('user can create findings inside a follow up', async ({
	page,
	logedPage,
	foldersPage,
	perimetersPage,
	findingsAssessmentsPage,
	findingsPage
}) => {
	//TODO: The first 2 steps are duplicated form business-impact-analysis.test.ts
	// They should be replaced when using the new create-fixture.py or create-tests-db.py approach
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

	await test.step('create follow up', async () => {
		await findingsAssessmentsPage.goto();
		await findingsAssessmentsPage.hasUrl();
		await findingsAssessmentsPage.createItem(testObjectsData.findingsAssessmentsPage.build);
	});

	await test.step('create finding inside follow up', async () => {
		await findingsAssessmentsPage.viewItemDetail(
			testObjectsData.findingsAssessmentsPage.build.name
		);
		await findingsPage.createItem({ name: vars.findingName }, undefined, page);
	});
});
