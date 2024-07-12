import { test, baseTest, expect, getUniqueValue } from '../../utils/test-utils.js';
import { LoginPage } from '../../utils/login-page.js';
import testData from '../../utils/test-data.js';

baseTest.beforeEach(async ({ page }) => {
	await page.goto('/');
});

baseTest.skip('login page as expected title', async ({ page }) => {
	await expect.soft(page.getByRole('heading', { name: 'Hello there 👋' })).toBeVisible();
});

test('login / logout process is working properly', async ({
	loginPage,
	analyticsPage,
	sideBar,
	page
}) => {
	await loginPage.hasUrl(1);
	await expect.soft(page.getByTestId('login')).toBeVisible();
	await loginPage.checkForUndefinedText();
	await loginPage.login();
	await analyticsPage.hasUrl();
	await sideBar.logout();
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

test('forgot password process is working properly', async ({
	logedPage,
	usersPage,
	sideBar,
	mailer,
	page
}) => {
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
	await usersPage.isToastVisible('Your password has been successfully set');

	await sideBar.logout();

	await logedPage.login(email, testData.user.password);
	await expect(page).toHaveURL(/.*\/analytics/);

	await sideBar.logout();

	await logedPage.forgotPasswordButton.click();
	await expect(page).toHaveURL('/password-reset');
	await logedPage.emailInput.fill(email);
	await logedPage.sendEmailButton.click();
	await logedPage.isToastVisible(
		'The request has been received, you should receive a reset link at the following address: ' +
			email
	);

	const lastMail = await mailer.getLastEmail();
	await lastMail.hasResetPasswordEmailDetails();
	await lastMail.hasEmailRecipient(email);

	await lastMail.open();
	const pagePromise = page.context().waitForEvent('page');
	await expect(mailer.emailContent.resetPasswordButton).toBeVisible();
	await mailer.emailContent.resetPasswordButton.click();
	const resetPasswordPage = await pagePromise;
	await resetPasswordPage.waitForLoadState();
	await expect(resetPasswordPage).toHaveURL(
		(await mailer.emailContent.resetPasswordButton.getAttribute('href')) ||
			'Reset password link could not be found'
	);

	const resetLoginPage = new LoginPage(resetPasswordPage);
	await resetLoginPage.newPasswordInput.fill('new' + testData.user.password);
	await resetLoginPage.confirmPasswordInput.fill('new' + testData.user.password);
	await resetLoginPage.setPasswordButton.click();

	await resetLoginPage.isToastVisible('Your password has been successfully reset');
	await resetLoginPage.hasUrl(0);
	await resetPasswordPage.close();

	// check that the old password is not working anymore
	await logedPage.usernameInput.fill(email);
	await logedPage.passwordInput.fill(testData.user.password);
	await logedPage.loginButton.click();
	await expect.soft(page.getByText('Unable to log in with provided credentials.')).toBeVisible();
	await logedPage.hasUrl();

	await logedPage.usernameInput.clear();
	await logedPage.passwordInput.clear();

	// login with the new password
	await logedPage.login(email, 'new' + testData.user.password);
	await expect(page).toHaveURL('/analytics');
});
