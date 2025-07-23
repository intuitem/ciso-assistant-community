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
			await expect(async () => {
				await sideBar.moreButton.click();
				await expect(sideBar.morePanel).not.toHaveAttribute('inert');
				await expect(sideBar.languageSelect).toBeVisible();
				setLocale(locale);
				await sideBar.languageSelect.selectOption(locale);
				await logedPage.hasTitle(m.analytics({}, { locale }));
			}).toPass();
		}
		await expect(async () => {
			await sideBar.moreButton.click();
			await expect(sideBar.morePanel).not.toHaveAttribute('inert');
			await expect(sideBar.languageSelect).toBeVisible();
			setLocale('en');
			await sideBar.languageSelect.selectOption('en');
			await logedPage.hasTitle(m.analytics({}, { locale: 'en' }));
		}).toPass();
	});
});
