import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('compliance assessments scoring is working properly', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	const testRequirements = ['folders', 'projects', 'complianceAssessments'];
	const IDAM1Score = {
		ratio: 0.66,
		progress: '75',
		value: 3
	};
	const IDAM2Score = {
		ratio: 0.33,
		progress: '50',
		value: 2
	};
	const IDBE1Score = {
		ratio: 0.99,
		progress: '100',
		value: 4
	};
	const PRAC1Score = {
		ratio: 0.0,
		progress: '25',
		value: 1
	};

	for (let requirement of testRequirements) {
		requirement += 'Page';
		const requiredPage = pages[requirement];

		await requiredPage.goto();
		await requiredPage.hasUrl();

		await requiredPage.createItem(
			testObjectsData[requirement].build,
			'dependency' in testObjectsData[requirement] ? testObjectsData[requirement].dependency : null
		);
	}

	await complianceAssessmentsPage.viewItemDetail(
		testObjectsData.complianceAssessmentsPage.build.name
	);

	// Click on the ID.AM-1 tree view item
	const IDAM1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-1', [
		'ID - Identify',
		'ID.AM - Asset Management'
	]);
	await IDAM1TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('slide-toggle').click({ force: true });
	await expect(page.getByTestId('progress-radial')).toHaveAttribute('aria-valuenow', '25');

	const IDAM1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDAM1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDAM1SliderBoundingBox.width * IDAM1Score.ratio,
				y: IDAM1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-radial')).toHaveAttribute(
		'aria-valuenow',
		IDAM1Score.progress
	);

	await complianceAssessmentsPage.form.saveButton.click();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDAM1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		IDAM1Score.progress
	);

	// Click on the ID.AM-2 tree view item
	const IDAM2TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-2', [
		'ID - Identify',
		'ID.AM - Asset Management'
	]);
	await IDAM2TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('slide-toggle').click({ force: true });
	await expect(page.getByTestId('progress-radial')).toHaveAttribute('aria-valuenow', '25');

	const IDAM2SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDAM2SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDAM2SliderBoundingBox.width * IDAM2Score.ratio,
				y: IDAM2SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-radial')).toHaveAttribute(
		'aria-valuenow',
		IDAM2Score.progress
	);

	await complianceAssessmentsPage.form.saveButton.click();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDAM2TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		IDAM2Score.progress
	);

	// Click on the ID.BE-1 tree view item
	const IDBE1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.BE-1', [
		'ID - Identify',
		'ID.BE - Business Environment'
	]);
	await IDBE1TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('slide-toggle').click({ force: true });
	await expect(page.getByTestId('progress-radial')).toHaveAttribute('aria-valuenow', '25');

	const IDBE1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDBE1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDBE1SliderBoundingBox.width * IDBE1Score.ratio,
				y: IDBE1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-radial')).toHaveAttribute(
		'aria-valuenow',
		IDBE1Score.progress
	);

	await complianceAssessmentsPage.form.saveButton.click();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDBE1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		IDBE1Score.progress
	);

	// Click on the PR.AC-1 tree view item
	const PRAC1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('PR.AC-1', [
		'PR - Protect',
		'PR.AC - Identity Management, Authentication and Access Control'
	]);
	await PRAC1TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('slide-toggle').click({ force: true });
	await expect(page.getByTestId('progress-radial')).toHaveAttribute('aria-valuenow', '25');

	const PRAC1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	PRAC1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: PRAC1SliderBoundingBox.width * PRAC1Score.ratio,
				y: PRAC1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-radial')).toHaveAttribute(
		'aria-valuenow',
		PRAC1Score.progress
	);

	await complianceAssessmentsPage.form.saveButton.click();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(PRAC1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		PRAC1Score.progress
	);

	// Assert that the computed compliance assessment score is correct
	const IDAMScore = (parseFloat(IDAM1Score.progress) + parseFloat(IDAM2Score.progress)) / 2;
	const IDScore = IDAMScore + (parseFloat(IDBE1Score.progress) - IDAMScore) / 3;
	const globalScore = IDScore + (parseFloat(PRAC1Score.progress) - IDScore) / 4;

	await expect(
		(
			await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM - Asset Management', [
				'ID - Identify'
			])
		).content.getByTestId('progress-radial')
	).toHaveAttribute('aria-valuenow', IDAMScore.toString());
	await expect(
		(
			await complianceAssessmentsPage.itemDetail.treeViewItem('ID - Identify', [])
		).content.getByTestId('progress-radial')
	).toHaveAttribute('aria-valuenow', IDScore.toString());
	await expect(page.getByTestId('progress-radial').first()).toHaveAttribute(
		'aria-valuenow',
		globalScore.toString()
	);
});

test.afterAll('cleanup', async ({ browser }) => {
	const page = await browser.newPage();
	const loginPage = new LoginPage(page);
	const foldersPage = new PageContent(page, '/folders', 'Domains');

	await loginPage.goto();
	await loginPage.login();
	await foldersPage.goto();
	await foldersPage.deleteItemButton(vars.folderName).click();
	await foldersPage.deleteModalConfirmButton.click();
	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
