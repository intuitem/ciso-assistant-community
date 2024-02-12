import { test } from '../utils/test-utils.js';

test('startup tests', async ({ loginPage, overviewPage, page }) => {
    await test.step('proper redirection to the login page', async () => {
        await page.goto('/');
        await loginPage.hasUrl(1);
        await loginPage.login();
        await overviewPage.hasUrl();
    });

    await test.step('proper redirection to the overview page after login', async () => {
        await overviewPage.hasUrl();
        await overviewPage.hasTitle();
    });
});
