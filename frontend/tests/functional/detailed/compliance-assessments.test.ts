import { TestContent, test, expect } from '../../utils/test-utils.js';

let vars = TestContent.generateTestVars();
let testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

test('risk acceptances can be processed', async ({ logedPage, pages, complianceAssessmentsPage, page }) => {
    const testRequirements = ["folders", "projects", "riskAssessments", "riskScenarios"];
    
    for (let requirement of testRequirements) {
        requirement += "Page";
        const requiredPage = pages[requirement];

        await requiredPage.goto();
        await requiredPage.hasUrl();

        await requiredPage.createItem(
            testObjectsData[requirement].build,
            'dependency' in testObjectsData[requirement] ? testObjectsData[requirement].dependency : null
        );
    };

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
    //TODO also test when setting another account as approver

    // Accept
    await riskAcceptancesPage.viewItemDetail(testObjectsData.riskAcceptancesPage.build.name + ' accepted');
    await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).toBeVisible();
    await riskAcceptancesPage.itemDetail.statusAcceptButton.click();

    await expect(riskAcceptancesPage.modalTitle).toBeVisible();
    await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
    await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
    await riskAcceptancesPage.modalConfirmButton.click();

    expect(await page.getByTestId('accepted-at-field-value').innerText()).not.toBe('--');
    await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).toBeVisible();
    
    // Revoke
    await riskAcceptancesPage.itemDetail.statusRevokeButton.click();

    await expect(riskAcceptancesPage.modalTitle).toBeVisible();
    await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
    await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
    await riskAcceptancesPage.modalConfirmButton.click();

    expect(await page.getByTestId('revoked-at-field-value').innerText()).not.toBe('--');
    await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).not.toBeVisible();
    
    // Reject
    await riskAcceptancesPage.goto();
    await riskAcceptancesPage.viewItemDetail(testObjectsData.riskAcceptancesPage.build.name + ' rejected');
    await expect(riskAcceptancesPage.itemDetail.statusRejectButton).toBeVisible();
    await riskAcceptancesPage.itemDetail.statusRejectButton.click();
    
    await expect(riskAcceptancesPage.modalTitle).toBeVisible();
    await expect(riskAcceptancesPage.modalCancelButton).toBeVisible();
    await expect(riskAcceptancesPage.modalConfirmButton).toBeVisible();
    await riskAcceptancesPage.modalConfirmButton.click();
    
    expect(await page.getByTestId('rejected-at-field-value').innerText()).not.toBe('--');
    await expect(riskAcceptancesPage.itemDetail.statusAcceptButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRejectButton).not.toBeVisible();
    await expect(riskAcceptancesPage.itemDetail.statusRevokeButton).not.toBeVisible();
});