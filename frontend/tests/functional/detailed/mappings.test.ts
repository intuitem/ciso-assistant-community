import { m } from '$paraglide/messages.js';
import { FormContent, FormFieldType } from '../../utils/form-content.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { expect, test, TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);
const FOLDER_WORKAROUND_SUFFIX = ' foo';
const PERIMETER_WORKAROUND_SUFFIX = ' bar';

test('user can import mappings', async ({
	page,
	logedPage,
	foldersPage,
	perimetersPage,
	mappingsPage,
	librariesPage
}) => {
	const importMappingBtn = page.getByTestId('import-button');

	await test.step('create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.hasUrl();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
		// NOTE: creating one more folder not to trip up the autocomplete test utils
		await foldersPage.createItem({
			name: vars.folderName + FOLDER_WORKAROUND_SUFFIX,
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
			name: vars.perimeterName + PERIMETER_WORKAROUND_SUFFIX,
			description: vars.description,
			folder: vars.folderName,
			ref_id: 'R.12345',
			lc_status: 'Production'
		});
	});

	await test.step('import mapping nist-csf-1.1 -> iso27001:2022', async () => {
		await mappingsPage.goto();
		await mappingsPage.hasUrl();
		await importMappingBtn.click();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary('Mapping from nist-csf-1.1 to iso27001-2022');
	});
});

test('user can map csf-1.1 audit to a new iso27001-2022 audit', async ({
	page,
	logedPage,
	mappingsPage,
	complianceAssessmentsPage
}) => {
	const IDAM1Score = {
		ratio: 0.66,
		progress: '75',
		value: 3
	};

	const applyMappingButton = page.getByTestId('apply-mapping-button');

	//NOTE: The form fields can't be passed to the PageContent constructor because the form is not an usual one
	const applyMappingForm = new FormContent(page, 'Create audit from baseline', [
		{ name: 'name', type: FormFieldType.TEXT },
		{ name: 'description', type: FormFieldType.TEXT },
		{ name: 'perimeter', type: FormFieldType.SELECT_AUTOCOMPLETE },
		{ name: 'framework', type: FormFieldType.SELECT_AUTOCOMPLETE }
	]);

	await test.step('create and score nist-csf-1.1 audit', async () => {
		await complianceAssessmentsPage.goto();
		await complianceAssessmentsPage.hasUrl();
		await complianceAssessmentsPage.createItem(
			testObjectsData.complianceAssessmentsPage.build,
			testObjectsData.complianceAssessmentsPage.dependency
		);

		// Click on the ID.AM-1 tree view item
		const IDAM1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-1', [
			'ID - Identify',
			'ID.AM - Asset Management'
		]);
		await IDAM1TreeViewItem.content.click();

		await page.waitForURL('/requirement-assessments/**');
		await page.getByTestId('switch').click({ force: true });
		if (!(await page.getByTestId('progress-ring-svg').isVisible())) {
			await page.getByTestId('switch').click({ force: true });
		}
		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('aria-valuenow', '1');

		const slider = page.getByTestId('range-slider-input');
		await expect(slider).toBeVisible();
		await slider.focus();
		for (let i = 1; i < IDAM1Score.value; i++) {
			await slider.press('ArrowRight');
		}
		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
			'aria-valuenow',
			IDAM1Score.value.toString()
		);

		await complianceAssessmentsPage.form.saveButton.click();
		await page.waitForURL(complianceAssessmentsPage.url + '/**');
		await expect(IDAM1TreeViewItem.progressRadial).toHaveAttribute(
			'aria-valuenow',
			IDAM1Score.progress
		);
	});

	await test.step('apply mapping to new iso27001:2022 audit', async () => {
		//NOTE: imitates PageContent.createItem(), since our form is not a "classic"" one
		// This could be improved
		await applyMappingButton.click();
		await applyMappingForm.hasTitle();
		if (page) {
			await page.waitForLoadState('networkidle');
		}
		await applyMappingForm.fill({
			name: 'Mapped-' + vars.assessmentName,
			description: vars.description,
			perimeter: vars.folderName + '/' + vars.perimeterName,
			framework: vars.framework.name
		});
		await applyMappingForm.saveButton.click();
		await expect(applyMappingForm.formTitle).not.toBeVisible();
		await complianceAssessmentsPage.isToastVisible(
			'The audit object has been successfully created',
			'i'
		);
	});
	await test.step('verify that mapping worked correctly', async () => {
		const IDAM1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-1', [
			'ID - Identify',
			'ID.AM - Asset Management'
		]);
		await IDAM1TreeViewItem.content.click();

		await page.waitForURL('/requirement-assessments/**');

		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
			'aria-valuenow',
			IDAM1Score.value.toString()
		);

		await complianceAssessmentsPage.form.saveButton.click();
		await page.waitForURL(complianceAssessmentsPage.url + '/**');
		await expect(IDAM1TreeViewItem.progressRadial).toHaveAttribute(
			'aria-valuenow',
			IDAM1Score.progress
		);
	});
});

async function deleteFolder(foldersPage: PageContent, folderName: string) {
	await foldersPage.deleteItemButton(folderName).click();
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();
}

test.afterAll('cleanup', async ({ browser }) => {
	const page = await browser.newPage();
	const loginPage = new LoginPage(page);
	const foldersPage = new PageContent(page, '/folders', 'Domains');

	await loginPage.goto();
	await loginPage.login();
	await foldersPage.goto();

	await deleteFolder(foldersPage, vars.folderName);
	await deleteFolder(foldersPage, vars.folderName + FOLDER_WORKAROUND_SUFFIX);

	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
	await page.close();
});
