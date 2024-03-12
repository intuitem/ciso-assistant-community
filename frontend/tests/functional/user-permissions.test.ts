import { LoginPage } from '../utils/login-page.js';
import { SideBar } from '../utils/sidebar.js';
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
    await usersPage.isToastVisible('The user: ' + vars.user.email + ' has been successfully updated.+');

    await sideBar.moreButton.click();
    await expect(sideBar.morePanel).not.toHaveAttribute('inert');
    await expect(sideBar.logoutButton).toBeVisible();
    await sideBar.logoutButton.click();
    await logedPage.hasUrl(0);
});

test('created user can log to his account', async ({
	mailer,
	page
}) => {
    await expect(mailer.page.getByText('{{').last()).toBeHidden(); // Wait for mailhog to load the emails
    const lastMail = await mailer.getLastEmail();
	await lastMail.hasWelcomeEmailDetails();
	await lastMail.hasEmailRecipient(vars.user.email);
	
	await lastMail.open();
	const pagePromise = page.context().waitForEvent('page');
	await mailer.emailContent.setPasswordButton.click();
	const setPasswordPage = await pagePromise;
	await setPasswordPage.waitForLoadState();
	await expect(setPasswordPage).toHaveURL(await mailer.emailContent.setPasswordButton.getAttribute('href') || 'Set password link could not be found');

	const setLoginPage = new LoginPage(setPasswordPage);
	await setLoginPage.newPasswordInput.fill(vars.user.password);
	await setLoginPage.confirmPasswordInput.fill(vars.user.password);
	await setLoginPage.setPasswordButton.click();
    
	await setLoginPage.isToastVisible('Your password has been successfully set. Welcome to CISO Assistant!');

    await setLoginPage.login(vars.user.email, vars.user.password);
    await expect(setLoginPage.page).toHaveURL('/analytics');

    // logout to prevent sessions conflicts
    const sideBar = new SideBar(setPasswordPage);
    await sideBar.moreButton.click();
    await expect(sideBar.morePanel).not.toHaveAttribute('inert');
    await expect(sideBar.logoutButton).toBeVisible();
    await sideBar.logoutButton.click();
    await setLoginPage.hasUrl(0);

    await setPasswordPage.close();
});

test.afterEach('cleanup', async ({ loginPage, foldersPage, usersPage, page }) => {
    await loginPage.login();
	await foldersPage.goto();
	await foldersPage.deleteItemButton(vars.folderName).click();
	await foldersPage.deleteModalConfirmButton.click();
	await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
	await usersPage.goto();
	await usersPage.deleteItemButton(vars.user.email).click();
	await usersPage.deleteModalConfirmButton.click();
	await expect(usersPage.getRow(vars.user.email)).not.toBeVisible();
});
