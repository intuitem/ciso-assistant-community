import { m } from '$paraglide/messages.js';
import { FormContent, FormFieldType } from '../../utils/form-content.js';
import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { expect, test, TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);
const FOLDER_WORKAROUND_SUFFIX = ' foo';

test('user can import required libraries and create required objects', async ({
	page,
	logedPage,
	foldersPage,
	librariesPage
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
			name: vars.folderName + FOLDER_WORKAROUND_SUFFIX,
			description: vars.description
		});
	});

	await test.step('import iso27001-2022 and csf-1.1', async () => {
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary(
			'International standard ISO/IEC 27001:2022',
			'urn:intuitem:risk:framework:iso27001-2022'
		);
		await librariesPage.goto();
		await librariesPage.hasUrl();
		await librariesPage.importLibrary('NIST CSF v1.1', 'urn:intuitem:risk:library:nist-csf-1.1');
	});
});

test('user can map iso27001-2022 audit to a new csf-1.1 audit', async ({
	page,
	logedPage,
	complianceAssessmentsPage
}) => {
	const IDAM1Score = {
		ratio: 0.66,
		progress: '75',
		value: 1
	};

	const OrgContextScore = {
		value: 75 / 5 + 1
	};

	const applyMappingButton = page.getByTestId('apply-mapping-button');

	//NOTE: The form fields can't be passed to the PageContent constructor because the form is not an usual one
	const applyMappingForm = new FormContent(page, 'Create audit from baseline', [
		{ name: 'name', type: FormFieldType.TEXT },
		{ name: 'description', type: FormFieldType.TEXT },
		{ name: 'folder', type: FormFieldType.SELECT_AUTOCOMPLETE },
		{ name: 'framework', type: FormFieldType.SELECT_AUTOCOMPLETE }
	]);

	await test.step('create and score iso27001-2022 audit', async () => {
		await complianceAssessmentsPage.goto();
		await complianceAssessmentsPage.hasUrl();
		await complianceAssessmentsPage.createItem({
			name: vars.assessmentName,
			description: vars.description,
			folder: vars.folderName,
			framework: 'International standard ISO/IEC 27001:2022'
		});

		// Enable scoring on the compliance assessment
		await page.getByTestId('edit-button').click();
		await page.getByText('More').click();
		for (const spinner of await page.locator('.loading-spinner').all()) {
			await expect(spinner).not.toBeVisible({
				timeout: 10_000
			});
		}
		await page.getByTestId('form-input-scoring-enabled').check();
		await page.getByTestId('save-button').click();

		await page.waitForTimeout(5000);

		const OrgContextTree = await complianceAssessmentsPage.itemDetail.treeViewItem(
			'4.1 - Understanding the organization and its context',
			['core - Clauses', '4 - Context of the organization']
		);
		await OrgContextTree.content.click();

		await page.waitForURL('/requirement-assessments/**');
		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('data-value', '0');

		const slider = page.getByTestId('range-slider-input');
		await expect(slider).toBeVisible();
		await slider.focus();
		for (let i = 1; i < OrgContextScore.value; i++) {
			await slider.press('ArrowRight');
		}
		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('data-value', '75');

		await page.getByTestId('save-no-continue-button').click();
		await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
		await page.goBack();
		await page.waitForURL(complianceAssessmentsPage.url + '/**');
		await expect(OrgContextTree.progressRadial).toHaveAttribute(
			'data-value',
			OrgContextScore.progress
		);
	});

	await test.step('apply mapping to new csf 1.1 audit', async () => {
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
			folder: vars.folderName,
			framework: vars.framework.name
		});
		await page.getByText('More').click();
		await page.getByTestId('form-input-scoring-enabled').check();
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
		for (const spinner of await page.locator('.loading-spinner').all()) {
			await expect(spinner).not.toBeVisible({
				timeout: 10_000
			});
		}

		await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
			'data-value',
			IDAM1Score.value.toString()
		);

		await page.getByTestId('save-no-continue-button').click();
		await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
		await page.goBack();
		await page.waitForURL(complianceAssessmentsPage.url + '/**');
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
