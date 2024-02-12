import { test, expect, setHttpResponsesListener, TestContent } from '../../utils/test-utils.js';

let vars: {[key: string]: any}; 

test.beforeEach(async ({ logedPage, foldersPage, sideBar, page }) => {
    await sideBar.click("General", foldersPage.url);
    await expect(page).toHaveURL(foldersPage.url);
    
    setHttpResponsesListener(page);
    vars = TestContent.itemBuilder();

    await foldersPage.createItem({
        name: vars.folderName, 
        description: vars.description
    });
});

test.describe('Tests on folder page', () => {

});

test.afterEach('cleanup', async ({ foldersPage, page }) => {
    await foldersPage.goto()
    await page.waitForURL(foldersPage.url);
    await foldersPage.deleteItemButton(vars.folderName).click();
    await foldersPage.deleteModalConfirmButton.click();
    await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
});