import { localItems } from '../../src/lib/utils/locales.js';
import { languageTag } from '../../src/paraglide/runtime.js';
import { test, expect, setHttpResponsesListener } from '../utils/test-utils.js';

type StringMap = {
	[key: string]: string;
};

test('sidebar navigation tests', async ({ logedPage, analyticsPage, sideBar, page }) => {
    test.slow();
    
    await test.step('proper redirection to the analytics page after login', async () => {
        await analyticsPage.hasUrl();
        await analyticsPage.hasTitle();
        setHttpResponsesListener(page);
    });
    
    await test.step('navigation link are working properly', async () => {
        //TODO delete this when page titles are fixed
        const temporaryPageTitle: StringMap = {
			'X-Rays': "X rays",
			'Backup & restore': "Backup restore"
        };
        
        for await (const [key, value] of sideBar.items) {            
            for await (const item of value) {
                if (item.href !== '/role-assignments') {
                    await sideBar.click(key, item.href);
                    await expect(page).toHaveURL(item.href);
                    if (item.name in temporaryPageTitle) {
                        await expect.soft(logedPage.pageTitle).toHaveText(temporaryPageTitle[item.name]);
                    } else {
                        await expect.soft(logedPage.pageTitle).toHaveText(item.name);
                    }
                }         
            }
        }
    });

    await test.step('user email is showing properly', async () => {
        await expect(page.getByTestId('sidebar-user-account-display')).toHaveText(logedPage.email);
        //TODO test also that user name and first name are displayed instead of the email when sets
    });
    
    await test.step('more panel links are working properly', async () => {
        await sideBar.moreButton.click();
        await expect(sideBar.morePanel).not.toHaveAttribute('inert');
        await expect(sideBar.profileButton).toBeVisible();
        await sideBar.profileButton.click();
        await expect(sideBar.morePanel).toHaveAttribute('inert');
        await expect(page).toHaveURL('/profile');
        await expect.soft(logedPage.pageTitle).toHaveText('Profile');
        
        await sideBar.moreButton.click();
        await expect(sideBar.morePanel).not.toHaveAttribute('inert');
        await expect(sideBar.aboutButton).toBeVisible();
        await sideBar.aboutButton.click();
        await expect(sideBar.morePanel).toHaveAttribute('inert');
        await expect(logedPage.modalTitle).toBeVisible();
        await expect.soft(logedPage.modalTitle).toHaveText('About CISO Assistant');
        await page.mouse.click(20, 20); // click outside the modal to close it
        await expect(logedPage.modalTitle).not.toBeVisible();
        
        await sideBar.moreButton.click();
        await expect(sideBar.morePanel).not.toHaveAttribute('inert');
        await expect(sideBar.logoutButton).toBeVisible();
        await sideBar.logoutButton.click();
        await logedPage.hasUrl(0);
    });
});

test('sidebar component tests', async ({ logedPage, sideBar, page }) => {
	await test.step('sidebar can be collapsed and expanded', async () => {
		sideBar.toggleButton.click();
		await expect(sideBar.toggleButton).toHaveClass(/rotate-180/);
		sideBar.toggleButton.click();
		await expect(sideBar.toggleButton).not.toHaveClass(/rotate-180/);
	});
});
