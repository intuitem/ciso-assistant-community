import { test, baseTest, expect, getUniqueValue } from '../../utils/test-utils.js';
import testData from '../../utils/test-data.js';

baseTest.beforeEach(async ({ page }) => {
	await page.goto('/');
});

baseTest.skip('login page as expected title', async ({ page }) => {
	await expect.soft(page.getByRole('heading', { name: 'Hello there 👋' })).toBeVisible();
});

test('login / logout process is working properly', async ({ loginPage, analyticsPage, sideBar, page }) => {
	await loginPage.hasUrl(1);
	await expect.soft(page.getByRole('heading', { name: 'Login into your account' })).toBeVisible();
	await loginPage.checkForUndefinedText();
	await loginPage.login();
	await analyticsPage.hasUrl();
	sideBar.moreButton.click();
	sideBar.logoutButton.click();
	await loginPage.hasUrl(0);
});

test('redirect to the right page after login', async ({ loginPage, page }) => {
	await page.goto('/login?next=/calendar');
	await loginPage.hasUrl(1);
	await loginPage.login();
	await expect(page).toHaveURL('/calendar');
});

test('login invalid message is showing properly', async ({ loginPage, page }) => {
	await loginPage.hasUrl();
	await loginPage.login('invalid@tests.com', '123456');
	await expect.soft(page.getByText('Unable to log in with provided credentials.')).toBeVisible();
	await loginPage.hasUrl();
});

test('forgot password link is working properly', async ({ logedPage, usersPage, sideBar, mailer, page }) => {
	const email = getUniqueValue(testData.user.email);
	
	await usersPage.goto();
	await usersPage.createItem({
		email: email
	});

	await usersPage.editItemButton(email).click();
	await page.getByTestId('set-password-btn').click();
	await expect(page).toHaveURL(/.*\/users\/.+\/edit\/set-password/);
	await usersPage.form.fill({
		new_password: testData.user.password,
		confirm_new_password: testData.user.password
	});
	await usersPage.form.saveButton.click();
	await usersPage.isToastVisible('The password was successfully set');

	await sideBar.moreButton.click();
	await expect(sideBar.morePanel).not.toHaveAttribute('inert');
	await expect(sideBar.logoutButton).toBeVisible();
	await sideBar.logoutButton.click();
	await logedPage.hasUrl(0);
	
	await logedPage.login(email, testData.user.password);
	await expect(page).toHaveURL(/.*\/analytics/);

	await sideBar.moreButton.click();
	await expect(sideBar.morePanel).not.toHaveAttribute('inert');
	await expect(sideBar.logoutButton).toBeVisible();
	await sideBar.logoutButton.click();
	await logedPage.hasUrl(0); 

	await logedPage.forgotPasswordButton.click();
	await expect(page).toHaveURL('/password-reset');
	await logedPage.emailInput.fill(email);
	await logedPage.sendEmailButton.click();
	await logedPage.isToastVisible('The request has been received, you should receive a reset link at the following address: ' + email);
	
	await mailer.goto();
	console.log(await (await mailer.lastEmail()).innerText());
	await logedPage.hasUrl(0);

	//TODO test that the email is received and the link is working properly
});
