import { LoginPage } from '../../utils/login-page.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

const workshopStepsNames = {
	11: 'Define the study framework',
	12: 'Define business and technical perimeter',
	13: 'Identify feared events',
	14: 'Determine the security foundation',
	21: 'Identify risk sources and targeted objectives',
	22: 'Evaluate RS/TO pairs',
	23: 'Select RS/TO pairs',
	31: 'Map the ecosystem',
	32: 'Develop strategic scenarios',
	33: 'Define security measures for the ecosystem',
	40: 'Prepare elementary actions',
	41: 'Develop operational scenarios',
	42: 'Evaluate the likelihood of operational scenarios',
	51: 'Generate the risk assessment',
	52: 'Decide on risk treatment strategy',
	53: 'Define security measures',
	54: 'Assess and document residual risks',
	55: 'Establish risk monitoring framework'
};

const ebiosRmStudy = {
	displayName: 'Ebios RM studies',
	modelName: 'ebiosrmstudy',
	dependency: vars.matrix,
	build: {
		name: 'Test Ebios RM Study',
		risk_matrix: vars.matrix.displayName,
		folder: vars.folderName
		// eta: "2025-01-01",
		// due_date: "2025-05-01"
	}
};

test('ebios rm study', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	assetsPage,
	librariesPage,
	ebiosRmStudyPage,
	complianceAssessmentsPage,
	appliedControlsPage,
	riskAssessmentsPage,
	page
}) => {
	test.setTimeout(900_000);
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
			name: ebiosRmStudy.build.name,
			folder: vars.folderName
		});
		await page.getByRole('gridcell', { name: ebiosRmStudy.build.name }).first().click();
	});

	await test.step('workshop 1', async () => {
		await test.step('step 1', async () => {
			await page.getByTestId('workshop-1-step-1-link').click();
			await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[11]], false);
			await page.getByRole('link', { name: ' Edit' }).click();
			await ebiosRmStudyPage.form.fill({
				authors: [LoginPage.defaultEmail],
				reviewers: [LoginPage.defaultEmail]
			});
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
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
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[12]], false);
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByTestId('select-button').click();
			await page.getByRole('textbox').click();
			await page.getByRole('option', { name: `${vars.folderName}/${vars.assetName}` }).click();
			await page.getByText(`Assets ${vars.folderName}/${vars.assetName}`).click();
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await assetsPage.createItem({ name: 'added asset' });
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
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[13]], false);
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
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
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
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
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
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
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[14]], false);
				await expect(page).toHaveURL(/.*\/ebios-rm\/[0-9a-f\-]+\/workshop-1.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await complianceAssessmentsPage.createItem({
				name: 'security foundation audit',
				perimeter: `${vars.folderName}/${vars.perimeterName}`,
				framework: vars.framework.name,
				authors: [LoginPage.defaultEmail]
			});
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 4 Determine the security' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
	});

	await test.step('workshop 2', async () => {
		await expect(async () => {
			await page.getByTestId('workshop-2-step-1-link').click();
			await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[21]], false);
			await expect(page).toHaveURL(/.*workshop-2.*/);
		}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
		await page.getByTestId('add-button').click();
		await page.getByTestId('form-input-risk-origin').getByRole('textbox').click();
		await page.getByRole('option', { name: 'Amateur' }).click();
		await page.getByTestId('form-input-target-objective').click();
		await page
			.getByTestId('form-input-target-objective')
			.fill(
				'Pariatur proident qui cupidatat nulla fugiat voluptate veniam nisi officia dolore consequat.'
			);
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
		await page
			.getByRole('listitem')
			.filter({ hasText: 'Step 1 Identify risk sources' })
			.getByTestId('sidebar-more-btn')
			.click();
		await page.getByRole('button', { name: 'Mark as done' }).click();
		await expect(async () => {
			await page.getByTestId('workshop-2-step-2-link').click();
			await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[22]], false);
			await expect(page).toHaveURL(/.*workshop-2.*/);
		}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
		await page.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-motivation').selectOption('3');
		await page.getByTestId('form-input-resources').selectOption('1');
		await page.getByTestId('form-input-activity').selectOption('3');
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
		await page
			.getByRole('listitem')
			.filter({ hasText: 'Step 2 Evaluate RS/TO pairs' })
			.getByTestId('sidebar-more-btn')
			.click();
		await page.getByRole('button', { name: 'Mark as done' }).click();
		await expect(async () => {
			await page.getByTestId('workshop-2-step-3-link').click();
			await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[23]], false);
			await expect(page).toHaveURL(/.*workshop-2.*/);
		}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
		await page.getByTestId('tablerow-edit-button').click();
		await page.getByTestId('form-input-is-selected').uncheck();
		await page.getByTestId('form-input-is-selected').check();
		await page.getByTestId('form-input-feared-events').getByRole('textbox').click();
		await page.getByRole('option', { name: `${vars.folderName}/test feared event 1` }).click();
		await page.getByRole('option', { name: `${vars.folderName}/test feared event 2` }).click();
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
		await page
			.getByRole('listitem')
			.filter({ hasText: 'Step 3 Select RS/TO pairs' })
			.getByTestId('sidebar-more-btn')
			.click();
		await page.getByRole('button', { name: 'Mark as done' }).click();
	});

	await test.step('workshop 3', async () => {
		await test.step('step 1', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-3-step-1-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[31]], false);
				await expect(page).toHaveURL(/.*workshop-3.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-category').getByRole('textbox').click();
			await page.getByRole('option', { name: 'partner' }).click();
			await page.getByText('4').first().click();
			await page.getByText('4').nth(1).click();
			await page.getByText('1', { exact: true }).nth(2).click();
			await page.getByText('1', { exact: true }).nth(3).click();
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('button', { name: ' Ecosystem radar +' }).click();
			await page.getByRole('button', { name: ' Ecosystem radar −' }).click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 1 Map the ecosystem' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
		await test.step('step 2', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-3-step-2-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[32]], false);
				await expect(page).toHaveURL(/.*workshop-3.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test strategic scenario 1');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.locator('div').filter({ hasText: 'Reminder: Do not forget to' }).nth(2).click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await expect(async () => {
				await page.getByTestId('workshop-3-step-2-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[32]], false);
				await expect(page).toHaveURL(/.*workshop-3.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByRole('gridcell', { name: 'test strategic scenario' }).click();
			await expect(page).not.toHaveURL(/.*workshop-3.*/);
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test attack path 1');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test attack path 2');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('link', { name: 'Develop strategic scenarios' }).click();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 2 Develop strategic' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
		await test.step('step 3', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-3-step-3-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[33]], false);
				await expect(page).toHaveURL(/.*workshop-3.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByRole('gridcell', { name: 'Partner' }).first().click();
			await expect(page).not.toHaveURL(/.*workshop-3.*/);
			await appliedControlsPage.createItem({ name: 'test applied control 1' });
			await appliedControlsPage.createItem({ name: 'test applied control 2' });
			await page.getByRole('link', { name: 'Define security measures for' }).click();
			await expect(page).toHaveURL(/.*workshop-3.*/);
			await page.getByTestId('tablerow-edit-button').click();
			await page
				.locator(
					'div:nth-child(4) > .flex.flex-col.space-y-4 > span > div:nth-child(3) > .p-1 > label:nth-child(3) > .text-base'
				)
				.first()
				.click();
			await page
				.locator(
					'div:nth-child(4) > .flex.flex-col.space-y-4 > span > div > .p-1 > label:nth-child(2) > .text-base'
				)
				.first()
				.click();
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 3 Define security measures for the ecosystem' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
	});
	await test.step('workshop 4', async () => {
		await test.step('step 0', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-4-step-0-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[40]], false);
				await expect(page).toHaveURL(/.*workshop-4.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test elementary action 1');
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('reconnaissance');
			await page.getByTestId('form-input-threat').getByRole('textbox').click();
			await page.getByText('Icon --').click();
			await page.getByTestId('form-input-icon').selectOption('cube');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-attack-stage').selectOption('1');
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('initial access');
			await page.getByTestId('form-input-icon').selectOption('server');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-attack-stage').selectOption('2');
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('DISCO');
			await page.getByTestId('form-input-icon').selectOption('diamond');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-attack-stage').selectOption('3');
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('exploitation');
			await page.getByTestId('form-input-icon').selectOption('skull');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('gridcell', { name: 'reconnaissance', exact: true }).click();
			await expect(page).not.toHaveURL(/.*workshop-4.*/);
			await page.getByRole('link', { name: 'Prepare elementary actions' }).click();
			await expect(page).toHaveURL(/.*workshop-4.*/);
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 0 Prepare elementary' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
		await test.step('step 1', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-4-step-1-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[41]], false);
				await expect(page).toHaveURL(/.*workshop-4.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-operating-modes-description').click();
			await page
				.getByTestId('form-input-operating-modes-description')
				.fill(
					'Minim ad dolore do pariatur non. Nostrud enim dolore est fugiat occaecat deserunt minim labore. Commodo minim adipisicing proident esse irure. Veniam nostrud et adipisicing.'
				);
			await page.getByTestId('form-input-threats').getByRole('textbox').click();
			await page.getByTestId('form-input-attack-path').getByRole('textbox').click();
			await page.getByRole('option', { name: 'test attack path 1' }).click();
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-operating-modes-description').click();
			await page
				.getByTestId('form-input-operating-modes-description')
				.fill(
					'Sint reprehenderit non sint dolor mollit non velit tempor ipsum culpa. Amet culpa voluptate est do aute tempor in aliquip ipsum dolore commodo nulla. Quis irure culpa dolore ad irure nisi ea deserunt in ad eu. Aliqua sunt voluptate et eu officia sit. Minim labore ea exercitation elit duis officia. Incididunt reprehenderit incididunt id deserunt quis. Ea irure Lorem cillum tempor. Voluptate ullamco et commodo veniam ex irure dolore dolore.'
				);
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 1 Develop operational' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
		await test.step('step 2', async () => {
			await expect(async () => {
				await page.getByTestId('workshop-4-step-2-link').click();
				await ebiosRmStudyPage.hasBreadcrumbPath([workshopStepsNames[42]], false);
				await expect(page).toHaveURL(/.*workshop-4.*/);
			}).toPass({ timeout: 80_000, intervals: [500, 1000, 2000] });
			await page.getByRole('gridcell', { name: 'test attack path 1' }).click();
			await expect(page).not.toHaveURL(/.*workshop-4.*/);
			await page.getByRole('button', { name: ' Severity High ' }).click();
			await page.getByRole('link', { name: ' Edit' }).click();
			await page.getByTestId('form-input-likelihood').selectOption('3');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('button', { name: ' Likelihood High ' }).click();
			await page.getByRole('button', { name: ' Risk level High ' }).click();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test operating mode 1');
			await page.getByTestId('form-input-likelihood').selectOption('1');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByTestId('add-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			for (const spinner of await page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 10_000
				});
			}
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('test operating mode 2');
			await page.getByTestId('form-input-likelihood').selectOption('4');
			await page.getByTestId('save-button').click();
			await expect(page.getByTestId('modal-title')).not.toBeVisible();
			await page.getByRole('link', { name: ' Go back to Ebios RM study' }).click();
			await page
				.getByRole('listitem')
				.filter({ hasText: 'Step 2 Evaluate the' })
				.getByTestId('sidebar-more-btn')
				.click();
			await page.getByRole('button', { name: 'Mark as done' }).click();
		});
	});

	await test.step('workshop 5', async () => {
		await page.getByRole('button', { name: ' Step 1 Generate the risk' }).click();
		await riskAssessmentsPage.form.fill({
			name: 'test-risk-assessment-ebios-rm',
			perimeter: `${vars.folderName}/${vars.perimeterName}`
		});
		await page.getByTestId('save-button').click();
		await expect(page.getByTestId('modal-title')).not.toBeVisible();
		await page
			.getByRole('gridcell', { name: 'test strategic scenario 1 - test attack path 1' })
			.click();
		await expect(page).not.toHaveURL(/.*workshop-5.*/);
		await expect(page.getByText('High').nth(2)).toBeVisible();
	});
});
