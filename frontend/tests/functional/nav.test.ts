import { safeTranslate } from '$lib/utils/i18n';
import { localItems } from '../../src/lib/utils/locales.js';
import { availableLanguageTags, setLanguageTag } from '../../src/paraglide/runtime.js';
import { expect, setHttpResponsesListener, test } from '../utils/test-utils.js';

test('sidebar navigation tests', async ({ logedPage, analyticsPage, sideBar, page }) => {
	test.slow();

	await test.step('proper redirection to the analytics page after login', async () => {
		await analyticsPage.hasUrl();
		await analyticsPage.hasTitle();
		setHttpResponsesListener(page);
	});

	await test.step('navigation link are working properly', async () => {
		for await (const [key, value] of sideBar.items) {
			for await (const item of value) {
				if (item.href !== '/role-assignments') {
					await sideBar.click(key, item.href, false);
					if (item.href === '/scoring-assistant' && (await logedPage.modalTitle.isVisible())) {
						await expect(logedPage.modalTitle).toBeVisible();
						await expect(logedPage.modalTitle).toHaveText(
							'Please import a risk matrix from the library to get access to this page'
						);
						await page.mouse.click(20, 20); // click outside the modal to close it
						await expect(logedPage.modalTitle).not.toBeVisible();
						continue;
					}
					await expect(page).toHaveURL(item.href);
					await logedPage.hasTitle(safeTranslate(item.name));
					//await logedPage.hasBreadcrumbPath([safeTranslate(item.name)]); //TODO: fix me
				}
			}
		}
	});

	await test.step('user email is showing properly', async () => {
		await expect(sideBar.userEmailDisplay).toHaveText(logedPage.email);
		//TODO test also that user name and first name are displayed instead of the email when sets
	});

	await test.step('user profile panel is working properly', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await logedPage.checkForUndefinedText();
		await expect(sideBar.profileButton).toBeVisible();
		await sideBar.profileButton.click();
		await expect(sideBar.morePanel).not.toBeVisible();
		await expect(page).toHaveURL('/my-profile');
		await expect.soft(logedPage.pageTitle).toHaveText('My profile');
		await logedPage.checkForUndefinedText();
	});

	await test.step('docs button is working properly and redirects to gitbook docs', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await logedPage.checkForUndefinedText();
		await expect(sideBar.docsButton).toBeVisible();
	});

	await test.step('translation panel is working properly', async () => {
		await analyticsPage.goto();
		const locales = [...availableLanguageTags];
		const index = locales.indexOf('en');
		if (index !== -1) {
			locales.splice(index, 1);
			locales.push('en');
		}
		for (const languageTag of locales) {
			await sideBar.moreButton.click();
			await expect(sideBar.morePanel).not.toHaveAttribute('inert');
			await expect(sideBar.languageSelect).toBeVisible();
			setLanguageTag(languageTag);
			const locales = localItems(languageTag);
			await sideBar.languageSelect.selectOption(languageTag);
			await logedPage.hasTitle(locales['analytics']);
		}
	});

	await test.step('about panel is working properly', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await logedPage.checkForUndefinedText();
		await expect(sideBar.aboutButton).toBeVisible();
		await sideBar.aboutButton.click();
		await expect(sideBar.morePanel).toHaveAttribute('inert');
		await expect(logedPage.modalTitle).toBeVisible();
		await expect.soft(logedPage.modalTitle).toHaveText('About CISO Assistant');
		await logedPage.checkForUndefinedText();
		await page.mouse.click(20, 20); // click outside the modal to close it
		await expect(logedPage.modalTitle).not.toBeVisible();

		await sideBar.logout();
	});
});

test('sidebar component tests', async ({ logedPage, sideBar }) => {
	await test.step('sidebar can be collapsed and expanded', async () => {
		sideBar.toggleButton.click();
		await expect(sideBar.toggleButton).toHaveClass(/rotate-180/);
		sideBar.toggleButton.click();
		await expect(sideBar.toggleButton).not.toHaveClass(/rotate-180/);
	});
});
