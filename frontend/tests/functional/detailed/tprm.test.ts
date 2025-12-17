import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';
import { SideBar } from '../../utils/sidebar.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

const entityAssessment = {
	name: 'Test entity assessment',
	perimeter: vars.perimeterName,
	create_audit: true,
	framework: vars.questionnaire.name,
	representatives: 'third-party@tests.com'
};

test('user can create representatives, solutions and entity assessments inside entity', async ({
	logedPage,
	foldersPage,
	perimetersPage,
	entitiesPage,
	representativesPage,
	solutionsPage,
	usersPage,
	entityAssessmentsPage,
	librariesPage,
	complianceAssessmentsPage,
	sideBar,
	mailer,
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

	await test.step('import questionnaire', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(vars.questionnaire.name, vars.framework.urn);
	});

	await test.step('create entity', async () => {
		await entitiesPage.goto();
		await entitiesPage.hasUrl();
		await entitiesPage.createItem(testObjectsData.entitiesPage.build);
		await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);
	});

	await test.step('create solution', async () => {
		await page.getByRole('tab', { name: 'Solutions' }).click();
		await expect(page.getByTestId('tabs-panel').getByText('Associated solutions')).toBeVisible();
		await solutionsPage.createItem(
			{
				name: 'Test solution'
			},
			undefined,
			undefined,
			'solution'
		);
	});

	await test.step('create representative', async () => {
		await page.getByRole('tab', { name: 'Representatives' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated representatives')
		).toBeVisible();
		await representativesPage.createItem(
			{
				email: 'third-party@tests.com',
				entity: testObjectsData.entitiesPage.build.name,
				create_user: true
			},
			undefined,
			undefined,
			'representative'
		);
	});

	await test.step('verify that user was created alongside representative', async () => {
		await page.getByRole('tab', { name: 'Representatives' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated representatives')
		).toBeVisible();
		await representativesPage.viewItemDetail('third-party@tests.com');
		await expect(page.getByTestId('user-field-value')).not.toBeEmpty();
		await page.getByTestId('user-field-value').locator('a').first().click();
		await usersPage.hasUrl();
		await usersPage.hasTitle('third-party@tests.com');
	});

	await test.step('go back to entity detail', async () => {
		await entitiesPage.goto();
		await entitiesPage.viewItemDetail(testObjectsData.entitiesPage.build.name);
	});

	await test.step('create entity assessment', async () => {
		await page.getByRole('tab', { name: 'Entity assessments' }).click();
		await expect(
			page.getByTestId('tabs-panel').getByText('Associated entity assessments')
		).toBeVisible();
		await entityAssessmentsPage.createItem(
			entityAssessment,
			undefined,
			undefined,
			'entity assessment'
		);
	});

	await test.step('verify that user was redirected to newly created entity assessment', async () => {
		await entityAssessmentsPage.hasUrl();
		await entityAssessmentsPage.hasTitle(entityAssessment.name);
	});

	await test.step('check that audit was created', async () => {
		await expect(page.getByTestId('compliance-assessment-field-value')).not.toBeEmpty();
		await page.getByTestId('compliance-assessment-field-value').locator('a').first().click();
		await complianceAssessmentsPage.hasUrl();
		await complianceAssessmentsPage.hasTitle(entityAssessment.name);
	});

	await test.step('check that third parties overview was updated', async () => {
		await page.goto('/analytics/tprm');
		await expect(page.locator('#page-title')).toHaveText('Overview');
		const cards = page.getByTestId('cards-list').locator('div');
		await expect(page.getByTestId('no-data-available')).not.toBeVisible();
		await expect(cards.first().getByTestId('provider')).toContainText(
			testObjectsData.entitiesPage.build.name,
			{
				ignoreCase: true
			}
		);
		await expect(cards.first().getByTestId('baseline')).toContainText(entityAssessment.framework, {
			ignoreCase: true
		});
	});

	await test.step('check that third parties overview cards can be flipped', async () => {
		const cards = page.getByTestId('cards-list').locator('div');
		await cards.first().getByTestId('flip-button-front').click();
		await expect(cards.first()).toHaveClass(/rotate-x-180/);

		// flip back to front
		await cards.first().getByTestId('flip-button-back').click();
		await expect(cards.first()).not.toHaveClass(/rotate-x-180/);
	});
});

test('third-party representative can set their password', async ({ sideBar, mailer, page }) => {
	test.slow();
	await test.step('set password and log in as third party representative', async () => {
		await expect(mailer.page.getByText('{{').last()).toBeHidden(); // Wait for mailhog to load the emails
		const lastMail = await mailer.getLastEmail();
		await lastMail.hasWelcomeEmailDetails();
		await lastMail.hasEmailRecipient('third-party@tests.com');

		await lastMail.open();
		const pagePromise = page.context().waitForEvent('page');
		await expect(mailer.emailContent.setPasswordButton).toBeVisible();
		await mailer.emailContent.setPasswordButton.click();
		const setPasswordPage = await pagePromise;
		await setPasswordPage.waitForLoadState();
		await expect(setPasswordPage).toHaveURL(
			(await mailer.emailContent.setPasswordButton.getAttribute('href')) ||
				'Set password link could not be found'
		);

		const setLoginPage = new LoginPage(setPasswordPage);
		await setLoginPage.newPasswordInput.fill(vars.thirdPartyUser.password);
		await setLoginPage.confirmPasswordInput.fill(vars.thirdPartyUser.password);
		if (
			setLoginPage.newPasswordInput.inputValue() !== vars.thirdPartyUser.password ||
			setLoginPage.confirmPasswordInput.inputValue() !== vars.thirdPartyUser.password
		) {
			await setLoginPage.newPasswordInput.fill(vars.thirdPartyUser.password);
			await setLoginPage.confirmPasswordInput.fill(vars.thirdPartyUser.password);
		}
		await setLoginPage.setPasswordButton.click();

		await setLoginPage.isToastVisible(
			'Your password has been successfully set. Welcome to CISO Assistant!'
		);

		await setLoginPage.login('third-party@tests.com', vars.thirdPartyUser.password);

		// third party user lands on compliance assessments page
		await expect(setLoginPage.page).toHaveURL('/compliance-assessments');

		// logout to prevent sessions conflicts
		const passwordPageSideBar = new SideBar(setPasswordPage);
		await passwordPageSideBar.logout();
	});
});

test('third-party representative can fill their assigned audit', async ({
	thirdPartyAuthenticatedPage,
	complianceAssessmentsPage,
	page
}) => {
	await test.step('third party representative can open their assigned audit', async () => {
		await complianceAssessmentsPage.hasUrl();
		await complianceAssessmentsPage.hasTitle('Audits');
		await complianceAssessmentsPage.viewItemDetail(entityAssessment.name);
	});

	await test.step('third party respondent can answer questions in table mode', async () => {
		await test.step('third party respondent can open table mode', async () => {
			await page.getByTestId('table-mode-button').click();
			await expect(page.getByTestId('requirement-assessments')).toBeVisible();
		});

		const assessableRequirements = page
			.getByRole('listitem')
			.filter({ has: page.getByRole('button', { name: /.*Observation.*/ }) });

		await test.step('third party respondent can fill questionnaire', async () => {
			await expect(assessableRequirements).not.toHaveCount(0);
			await page.getByRole('button', { name: 'Yes' }).first().click();
			await page.getByRole('button', { name: 'No' }).nth(1).click();
			await page.getByRole('button', { name: 'N/A' }).nth(2).click();
			await page.getByRole('button', { name: 'Yes' }).nth(3).click();
			await page.getByRole('button', { name: 'No' }).nth(4).click();
			await page.getByRole('button', { name: 'N/A' }).nth(5).click();
		});

		await test.step('third party respondent can create evidence', async () => {
			await assessableRequirements
				.first()
				.getByRole('button', { name: /.*Evidence.*/ })
				.click();
			await assessableRequirements.first().getByTestId('create-evidence-button').click();
			await page.getByTestId('form-input-name').click();
			await page.getByTestId('form-input-name').fill('tp-evidence');
			await page.getByTestId('form-input-filtering-labels').getByRole('textbox').click();
			await page.getByTestId('save-button').click();
			await complianceAssessmentsPage.isToastVisible(
				'The evidence object has been successfully created' + /.+/.source
			);
		});

		await test.step('check that evidence count was updated', async () => {
			await expect(assessableRequirements.first().getByTestId('evidence-count')).toContainText('1');
		});

		await test.step('check that selected evidences were updated', async () => {
			await assessableRequirements.first().getByTestId('select-evidence-button').click();
			await expect(page.getByTestId('modal-title')).toBeVisible();
			await expect(page.getByRole('option').first()).toContainText(/.*tp-evidence.*/);
			await page.getByTestId('cancel-button').click();
		});

		await test.step('check modified requirement assessment', async () => {
			await page.getByTestId('back-to-audit').click();

			await complianceAssessmentsPage.hasUrl();
			await complianceAssessmentsPage.hasTitle(entityAssessment.name);
			const editedRequirementAssessment = await complianceAssessmentsPage.itemDetail.treeViewItem(
				'AC.L1-3.1.1 - Authorized Access Control',
				['AC - ACCESS CONTROL']
			);
			editedRequirementAssessment.content.click();
			await page.waitForURL('/requirement-assessments/**');
			await expect(page.getByRole('button', { name: 'Yes' }).first()).toHaveClass(
				/.*preset-filled.*/
			);
			await expect(page.getByRole('button', { name: 'No' }).nth(1)).toHaveClass(
				/.*preset-filled.*/
			);
			await expect(page.getByRole('button', { name: 'N/A' }).nth(2)).toHaveClass(
				/.*preset-filled.*/
			);
			await expect(page.getByRole('button', { name: 'Yes' }).nth(3)).toHaveClass(
				/.*preset-filled.*/
			);
			await expect(page.getByRole('button', { name: 'No' }).nth(4)).toHaveClass(
				/.*preset-filled.*/
			);
			await expect(page.getByRole('button', { name: 'N/A' }).nth(5)).toHaveClass(
				/.*preset-filled.*/
			);
		});
	});
});

test.afterAll('cleanup', async ({ browser }) => {
	const page = await browser.newPage();
	const loginPage = new LoginPage(page);
	const foldersPage = new PageContent(page, '/folders', 'Domains');

	await loginPage.goto();
	await loginPage.login();
	await foldersPage.goto();

	await foldersPage.deleteItemButton(vars.folderName).click();
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();

	await foldersPage.deleteItemButton(vars.folderName + ' foo').click();
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();

	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
