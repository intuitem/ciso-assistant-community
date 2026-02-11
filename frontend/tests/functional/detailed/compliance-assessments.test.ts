import { LoginPage } from '../../utils/login-page.js';
import { PageContent } from '../../utils/page-content.js';
import { TestContent, test, expect } from '../../utils/test-utils.js';
import { m } from '$paraglide/messages';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('compliance assessments scoring is working properly', async ({
	logedPage,
	pages,
	complianceAssessmentsPage,
	page
}) => {
	const testRequirements = ['folders', 'perimeters', 'complianceAssessments'];
	const maxScore = 4;
	const IDAM1Score = {
		ratio: 0.66,
		value: 3
	};
	const IDAM2Score = {
		ratio: 0.33,
		value: 2
	};
	const IDBE1Score = {
		ratio: 0.99,
		value: 4
	};
	const PRAC1Score = {
		ratio: 0.0,
		value: 1
	};
	// Helper to convert raw score to percentage for tree view assertions
	const toPercent = (score: number) => ((score / maxScore) * 100).toString();

	for (let requirement of testRequirements) {
		requirement += 'Page';
		const requiredPage = pages[requirement];

		await requiredPage.goto();
		await requiredPage.hasUrl();

		await requiredPage.createItem(
			testObjectsData[requirement].build,
			'dependency' in testObjectsData[requirement] ? testObjectsData[requirement].dependency : null
		);

		await requiredPage.goto();
		await requiredPage.hasUrl();
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
	await page.getByTestId('switch').click({ force: true });
	if (!page.getByTestId('progress-ring-svg').isVisible()) {
		await page.getByTestId('switch').click({ force: true });
	}
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('aria-valuenow', '1');

	const IDAM1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDAM1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDAM1SliderBoundingBox.width * IDAM1Score.ratio,
				y: IDAM1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
		'aria-valuenow',
		IDAM1Score.value.toString()
	);

	await page.getByTestId('save-no-continue-button').click();
	await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
	await page.goBack();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDAM1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		toPercent(IDAM1Score.value)
	);

	// Click on the ID.AM-2 tree view item
	const IDAM2TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM-2', [
		'ID - Identify',
		'ID.AM - Asset Management'
	]);
	await IDAM2TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('switch').click({ force: true });
	if (!page.getByTestId('progress-ring-svg').isVisible()) {
		await page.getByTestId('switch').click({ force: true });
	}
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('aria-valuenow', '1');

	const IDAM2SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDAM2SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDAM2SliderBoundingBox.width * IDAM2Score.ratio,
				y: IDAM2SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
		'aria-valuenow',
		IDAM2Score.value.toString()
	);

	await page.getByTestId('save-no-continue-button').click();
	await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
	await page.goBack();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDAM2TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		toPercent(IDAM2Score.value)
	);

	// Click on the ID.BE-1 tree view item
	const IDBE1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('ID.BE-1', [
		'ID - Identify',
		'ID.BE - Business Environment'
	]);
	await IDBE1TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('switch').click({ force: true });
	if (!page.getByTestId('progress-ring-svg').isVisible()) {
		await page.getByTestId('switch').click({ force: true });
	}
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('aria-valuenow', '1');

	const IDBE1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	IDBE1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: IDBE1SliderBoundingBox.width * IDBE1Score.ratio,
				y: IDBE1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
		'aria-valuenow',
		IDBE1Score.value.toString()
	);

	await page.getByTestId('save-no-continue-button').click();
	await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
	await page.goBack();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(IDBE1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		toPercent(IDBE1Score.value)
	);

	// Click on the PR.AC-1 tree view item
	const PRAC1TreeViewItem = await complianceAssessmentsPage.itemDetail.treeViewItem('PR.AC-1', [
		'PR - Protect',
		'PR.AC - Identity Management, Authentication and Access Control'
	]);
	await PRAC1TreeViewItem.content.click();

	await page.waitForURL('/requirement-assessments/**');
	await page.getByTestId('switch').click({ force: true });
	if (!page.getByTestId('progress-ring-svg').isVisible()) {
		await page.getByTestId('switch').click({ force: true });
	}
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute('aria-valuenow', '1');

	const PRAC1SliderBoundingBox = await page.getByTestId('range-slider-input').boundingBox();
	PRAC1SliderBoundingBox &&
		(await page.getByTestId('range-slider-input').click({
			position: {
				x: PRAC1SliderBoundingBox.width * PRAC1Score.ratio,
				y: PRAC1SliderBoundingBox.height / 2
			}
		}));
	await expect(page.getByTestId('progress-ring-svg')).toHaveAttribute(
		'aria-valuenow',
		PRAC1Score.value.toString()
	);

	await page.getByTestId('save-no-continue-button').click();
	await complianceAssessmentsPage.isToastVisible('successfully saved', 'i');
	await page.goBack();
	await page.waitForURL(complianceAssessmentsPage.url + '/**');
	await expect(PRAC1TreeViewItem.progressRadial).toHaveAttribute(
		'aria-valuenow',
		toPercent(PRAC1Score.value)
	);

	// Assert that the computed compliance assessment score is correct
	// Raw score calculations (as computed by backend)
	const IDAMScoreRaw = (IDAM1Score.value + IDAM2Score.value) / 2;
	const IDScoreRaw = IDAMScoreRaw + (IDBE1Score.value - IDAMScoreRaw) / 3;
	const globalScoreRaw = IDScoreRaw + (PRAC1Score.value - IDScoreRaw) / 4;

	// TreeViewItemContent uses Skeleton ProgressRing with percentage values
	await expect(
		(
			await complianceAssessmentsPage.itemDetail.treeViewItem('ID.AM - Asset Management', [
				'ID - Identify'
			])
		).content.getByTestId('progress-ring-svg')
	).toHaveAttribute('aria-valuenow', ((IDAMScoreRaw / maxScore) * 100).toString());
	await expect(
		(
			await complianceAssessmentsPage.itemDetail.treeViewItem('ID - Identify', [])
		).content.getByTestId('progress-ring-svg')
	).toHaveAttribute('aria-valuenow', ((IDScoreRaw / maxScore) * 100).toString());

	// Global RingProgress (next to donut) uses raw score
	await expect(page.getByTestId('progress-ring-svg').first()).toHaveAttribute(
		'aria-valuenow',
		globalScoreRaw.toString()
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
	await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
	await foldersPage.deletePromptConfirmTextField().fill(m.yes());
	await foldersPage.deletePromptConfirmButton().click();
	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});
