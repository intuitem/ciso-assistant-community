import { test, expect, setHttpResponsesListener, TestContent } from '../utils/test-utils.js';

const vars = TestContent.generateTestVars();

test.beforeEach('create user', async ({ logedPage, usersPage, foldersPage, sideBar, page }) => {
    setHttpResponsesListener(page);

    await foldersPage.goto();
    await foldersPage.createItem({
        name: vars.folderName,
        description: vars.description
    });

    await usersPage.goto();
    await usersPage.createItem({
        email: vars.user.email
    });

    await usersPage.editItemButton(vars.user.email).click();
    await usersPage.form.fill({
        first_name: vars.user.firstName,
        last_name: vars.user.lastName, 
        user_groups: [
            `${vars.folderName} - ${vars.usergroups.analyst}`,
            `${vars.folderName} - ${vars.usergroups.auditor}`,
            `${vars.folderName} - ${vars.usergroups.domainManager}`,
            `${vars.folderName} - ${vars.usergroups.approver}`,
        ],
    });
    await usersPage.form.saveButton.click();
    await usersPage.isToastVisible('.+ successfully saved: ' + vars.user.email);
    
    page.on('dialog', dialog => dialog.accept()); // Accept the alert dialog

    await usersPage.editItemButton(vars.user.email).click();
    await page.getByTestId('set-password-btn').click();
    await expect(page).toHaveURL(/.*\/users\/.+\/edit\/set-password/);
    await usersPage.form.fill({
        new_password: vars.user.password,
        confirm_new_password: vars.user.password
    });
    await usersPage.form.saveButton.click();
    await usersPage.isToastVisible('The password was successfully set');

    await sideBar.moreButton.click();
    await expect(sideBar.morePanel).not.toHaveAttribute('inert');
    await expect(sideBar.logoutButton).toBeVisible();
    await sideBar.logoutButton.click();
    await logedPage.hasUrl(0);
});

test('created user can log to his account', async ({
	loginPage,
	page
}) => {
	await loginPage.login(vars.user.email, vars.user.password);
    await expect(page).toHaveURL(/.*\/analytics/);
});

test.afterEach('cleanup', async ({ loginPage, sideBar, foldersPage, usersPage, page }) => {
    if (loginPage.email === vars.user.email) {
        await sideBar.moreButton.click();
        await expect(sideBar.morePanel).not.toHaveAttribute('inert');
        await expect(sideBar.logoutButton).toBeVisible();
        await sideBar.logoutButton.click();
        await loginPage.hasUrl(0);
        await loginPage.login();
    }
	await foldersPage.goto();
	await foldersPage.deleteItemButton(vars.folderName).click();
	await foldersPage.deleteModalConfirmButton.click();
	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();

	await usersPage.goto();
	await usersPage.deleteItemButton(vars.user.email).click();
	await usersPage.deleteModalConfirmButton.click();
	await expect(usersPage.getRow(vars.user.email)).not.toBeVisible();
});
