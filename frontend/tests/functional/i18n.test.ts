import { locales, setLocale } from '../../src/paraglide/runtime.js';
import { expect, test } from '../utils/test-utils.js';
import { m } from '$paraglide/messages';

test('switching locale works properly', async ({ logedPage, analyticsPage, sideBar, page }) => {
	await test.step('translation panel is working properly', async () => {
		await analyticsPage.goto();
		const allLocales = [...locales];
		const index = allLocales.indexOf('en');
		if (index !== -1) {
			allLocales.splice(index, 1);
			allLocales.push('en');
		}
		for (const locale of allLocales) {
			await sideBar.moreButton.click();
			await expect(sideBar.morePanel).not.toHaveAttribute('inert');
			await expect(sideBar.languageSelect).toBeVisible();
			setLocale(locale);
			if (!sideBar.languageSelect.isVisible()) {
				await sideBar.moreButton.click();
				await expect(sideBar.morePanel).not.toHaveAttribute('inert');
				await expect(sideBar.languageSelect).toBeVisible();
			}
			await sideBar.languageSelect.selectOption(locale);
			await logedPage.hasTitle(m.analytics({}, { locale }));
		}
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await expect(sideBar.languageSelect).toBeVisible();
		setLocale('en');
		if (!sideBar.languageSelect.isVisible()) {
			await sideBar.moreButton.click();
			await expect(sideBar.morePanel).not.toHaveAttribute('inert');
			await expect(sideBar.languageSelect).toBeVisible();
		}
		await sideBar.languageSelect.selectOption('en');
		await logedPage.hasTitle(m.analytics({}, { locale: 'en' }));
	});
});
