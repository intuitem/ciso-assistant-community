import { test, baseTest, expect } from '../../utils/test-utils.js';

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

//TODO add test for the "forgot password" link
