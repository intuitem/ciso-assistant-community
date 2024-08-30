import { TestContent, test, expect } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();
const testObjectsData: Record<string, any> = TestContent.itemBuilder(vars);

test('risk acceptances can be processed', async ({
	pages,
	usersPage,
	riskAcceptancesPage,
	page
}) => {
	const testRequirements = ['users', 'folders', 'projects', 'riskAssessments', 'riskScenarios'];

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

	await usersPage.goto();
	await usersPage.editItemButton(vars.user.email).click();
	await usersPage.form.fill({
		user_groups: [`${vars.folderName} - ${vars.usergroups.reader.name}`]
	});
	await usersPage.form.saveButton.click();
	await usersPage.isToastVisible(
		'The user: ' + vars.user.email + ' has been successfully updated.+'
	);

	await riskAcceptancesPage.goto();
	await riskAcceptancesPage.hasUrl();

	await riskAcceptancesPage.createItem({
		...testObjectsData.riskAcceptancesPage.build,
		name: testObjectsData.riskAcceptancesPage.build.name + ' accepted'
	});
	await riskAcceptancesPage.createItem({
		...testObjectsData.riskAcceptancesPage.build,
		name: testObjectsData.riskAcceptancesPage.build.name + ' rejected'
	});

	// Check that a non approver user can't accept the risk acceptance
	await riskAcceptancesPage.addButton.click();
	await page.getByTestId('form-input-approver').click();
	await expect(
		page.getByRole('option', { name: vars.user.email, exact: true }).first()
	).toBeHidden();
	await riskAcceptancesPage.goto();

	// Accept
	await riskAcceptancesPage.viewItemDetail(
		testObjectsData.riskAcceptancesPage.build.name + ' accepted'
	);
	await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).toBeVisible();
	await riskAcceptancesPage.itemDetail.statusAcceptButton.click();

	await expect(riskAcceptancesPage.modalTitle).toBeVisible();
	await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
	await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
	await riskAcceptancesPage.modalConfirmButton.click();

	expect(await page.getByTestId('accepted-at-field-value')).toHaveText(/\d+\/\d+\/\d+,.+/);
	await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).toBeVisible();

	// Revoke
	await riskAcceptancesPage.itemDetail.statusRevokeButton.click();

	await expect(riskAcceptancesPage.modalTitle).toBeVisible();
	await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
	await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
	await riskAcceptancesPage.modalConfirmButton.click();

	expect(await page.getByTestId('revoked-at-field-value')).toHaveText(/\d+\/\d+\/\d+,.+/);
	await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).not.toBeVisible();

	// Reject
	await riskAcceptancesPage.goto();
	await riskAcceptancesPage.viewItemDetail(
		testObjectsData.riskAcceptancesPage.build.name + ' rejected'
	);
	await expect(riskAcceptancesPage.itemDetail.statusRejectButton).toBeVisible();
	await riskAcceptancesPage.itemDetail.statusRejectButton.click();

	await expect(riskAcceptancesPage.modalTitle).toBeVisible();
	await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
	await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
	await riskAcceptancesPage.modalConfirmButton.click();

	expect(await page.getByTestId('rejected-at-field-value')).toHaveText(/\d+\/\d+\/\d+,.+/);
	await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
	await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).not.toBeVisible();
});
