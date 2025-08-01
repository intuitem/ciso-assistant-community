import { LoginPage } from '../../utils/login-page.js';
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
			name: 'additional perimeter',
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.1234',
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
	});

	await test.step('import risk matrix', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.matrix.name, vars.matrix.urn);
	});

	await test.step('import framework', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.framework.name, vars.framework.urn);
	});

	await test.step('create ebios rm study', async () => {
		await page.goto('/ebios-rm');
		await ebiosRmStudyPage.hasUrl();
		await ebiosRmStudyPage.hasTitle();
		await ebiosRmStudyPage.createItem({
			name: testObjectsData.ebiosRmStudyPage.build.name,
			folder: vars.folderName
		});
		await page.getByRole('gridcell', { name: testObjectsData.ebiosRmStudyPage.build.name }).click();
	});

	await test.step('workshop 1', async () => {
		await test.step('step 1', async () => {
			await page.getByTestId('workshop-1-step-1-link').click();
			await page.getByRole('link', { name: ' Edit' }).click();
			await ebiosRmStudyPage.form.fill({
				authors: [LoginPage.defaultEmail],
				reviewers: [LoginPage.defaultEmail]
			});
			await page.getByTestId('save-button').click();
			await expect(
				page
					.locator('#activityOne div')
					.filter({ hasText: `Authors ${LoginPage.defaultEmail}` })
					.getByRole('link')
			).toBeVisible();
			await expect(
				page
					.locator('#activityOne div')
					.filter({ hasText: `Reviewers ${LoginPage.defaultEmail}` })
					.getByRole('link')
			).toBeVisible();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 1 Define the study' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});

		await test.step('step 2', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-1-step-2-link').click();
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/, { timeout: 2000 });
			}).toPass({ timeout: 10000, intervals: [500, 1000, 2000] });
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
			await expect(async () => {
				await page.getByTestId('workshop-1-step-3-link').click();
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/, { timeout: 2000 });
			}).toPass({ timeout: 10000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test feared event 1');
			await page.getByTestId('form-input-gravity').selectOption('3');
			await page.getByTestId('form-input-assets').getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/added asset Primary` }).click();
			await page.getByTestId('form-input-qualifications').getByRole('textbox').click();
			await page.getByRole('option', { name: 'Authenticity' }).click();
			await page.getByRole('option', { name: 'Availability' }).click();
			await page.getByTestId('save-button').press('Enter');
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
			await page.getByTestId('save-button').press('Enter');
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 3 Identify feared events' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});

		await test.step('step 4', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-1-step-4-link').click();
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/, { timeout: 2000 });
			}).toPass({ timeout: 10000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('security foundation audit');
			await page.getByTestId('form-input-perimeter').getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/${vars.perimeterName}` }).click();
			await page.getByTestId('form-input-framework').getByRole('searchbox').click();
			await page.getByRole('option', { name: vars.framework.name }).click();
			await page.getByTestId('form-input-authors').getByRole('textbox').click();
			await page.getByRole('option', { name: LoginPage.defaultEmail }).click();
			await page.getByTestId('save-button').press('Enter');
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
