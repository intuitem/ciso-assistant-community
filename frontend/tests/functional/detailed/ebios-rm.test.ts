import { TestContent, test, expect } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('ebios rm study', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	assetsPage,
	librariesPage,
	ebiosRmStudyPage,
	page
}) => {
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

	await test.step('create required assets', async () => {
		await assetsPage.goto();
		await assetsPage.hasUrl();
		await assetsPage.createItem({
			name: vars.assetName,
			description: vars.description,
			folder: vars.folderName,
			type: 'Primary'
		});
		// NOTE: creating one more asset not to trip up the autocomplete test utils
		await assetsPage.createItem({
			name: vars.assetName + ' foo',
			description: vars.description,
			folder: vars.folderName,
			type: 'Primary'
		});
	});

	await test.step('import risk matrix', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.matrix.name, vars.matrix.urn);
	});

	await test.step('create ebios rm study', async () => {
		await page.goto('/ebios-rm');
		await ebiosRmStudyPage.hasUrl();
		await ebiosRmStudyPage.hasTitle();
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-name').click();
		await page.getByTestId('form-input-name').fill('test ebios rm study');
		await page.getByTestId('form-input-folder').getByRole('textbox').click();
		await page.getByRole('option', { name: 'DEMO' }).click();
		await page.getByTestId('save-button').click();
		await page.getByRole('gridcell', { name: 'test ebios rm study' }).click();
	});

	await test.step('workshop 1', async () => {
		await test.step('step 1', async () => {
			await page.getByRole('link', { name: 'Step 1 Define the study' }).click();
			await page.getByRole('link', { name: ' Edit' }).click();
			await page.getByTestId('form-input-authors').getByRole('textbox').click();
			await page.getByRole('option', { name: vars.user.email }).click();
			await page.getByTestId('form-input-reviewers').getByRole('textbox').click();
			await page
				.getByTestId('form-input-reviewers')
				.getByRole('option', { name: vars.user.email })
				.click();
			await page.getByTestId('save-button').click();
			await page
				.locator('#activityOne div')
				.filter({ hasText: `Authors ${vars.user.email}` })
				.getByRole('link')
				.click();
			await page
				.locator('#activityOne div')
				.filter({ hasText: `Reviewers ${vars.user.email}` })
				.getByRole('link')
				.click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 1 Define the study' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});

		await test.step('step 2', async () => {
			await page.getByRole('link', { name: 'Step 2 Define business and' }).click();
			await page.getByTestId('select-button').click();
			await page.getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/${vars.assetName}` }).click();
			await page.getByText(`Assets ${vars.folderName}/${vars.assetName}`).click();
			await page.getByTestId('save-button').click();
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('added asset');
			await page.getByTestId('save-button').click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 2 Define business and' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});

		await test.step('step 3', async () => {
			await page.getByRole('link', { name: 'Step 3 Identify feared events' }).click();
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test feared event 1');
			await page.getByTestId('form-input-gravity').selectOption('3');
			await page.getByTestId('form-input-assets').getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/added asset Primary` }).click();
			await page.getByTestId('form-input-qualifications').getByRole('textbox').click();
			await page.getByRole('option', { name: 'Authenticity' }).click();
			await page.getByRole('option', { name: 'Availability' }).click();
			await page.getByTestId('save-button').click();
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test feared event 2');
			await page.getByTestId('form-input-gravity').selectOption('1');
			await page.getByTestId('form-input-assets').getByRole('textbox').click();
			await page
				.getByRole('option', { name: `${vars.folderName}/${vars.assetName} Primary` })
				.click();
			await page.getByTestId('form-input-qualifications').getByRole('textbox').click();
			await page.getByRole('option', { name: 'Environmental' }).click();
			await page.getByTestId('form-input-qualifications').getByRole('textbox').press('Escape');
			await page.getByTestId('save-button').click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 3 Identify feared events' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});

		await test.step('step 4', async () => {
			await page.getByRole('link', { name: 'Step 4 Determine the security' }).click();
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('security foundation audit');
			await page.getByTestId('form-input-perimeter').getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/${vars.perimeterName}` }).click();
			await page.getByTestId('form-input-framework').getByRole('searchbox').click();
			await page.getByRole('option', { name: 'NIST CSF v2.0' }).click();
			await page.getByTestId('form-input-authors').getByRole('textbox').click();
			await page.getByRole('option', { name: vars.user.email }).click();
			await page.getByTestId('save-button').click();
			await expect(page.getByRole('gridcell', { name: 'security foundation audit' })).toBeVisible();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 4 Determine the security' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
	});
});
