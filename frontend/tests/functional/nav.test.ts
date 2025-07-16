import { safeTranslate } from '$lib/utils/i18n';
import { locales, setLocale } from '../../src/paraglide/runtime.js';
import { expect, setHttpResponsesListener, test } from '../utils/test-utils.js';
import { m } from '$paraglide/messages';

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
					if (item.href === '/calendar') {
						const currentDate = new Date();
						const year = currentDate.getFullYear();
						const month = currentDate.getMonth() + 1;
						await expect(page).toHaveURL(`/calendar/${year}/${month}`);
					} else await expect(page).toHaveURL(item.href);
					await logedPage.hasTitle(safeTranslate(item.name));
					//await logedPage.hasBreadcrumbPath([safeTranslate(item.name)]); //TODO: fix me
				}
			}
		}
	});
});

test('more panel components work properly', async ({ logedPage, sideBar, page }) => {
	await test.step('user email is showing properly', async () => {
		await expect(sideBar.userEmailDisplay).toHaveText(logedPage.email);
	});

	await test.step('user name and first name are displayed instead of email when set', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await sideBar.profileButton.click();
		await expect(page).toHaveURL('/my-profile');

		await page.getByText('Edit').click();
		const testFirstName = 'Eric';
		const testLastName = 'Abder';
		await page.getByTestId('form-input-first-name').fill(testFirstName);
		await page.getByTestId('form-input-last-name').fill(testLastName);
		await page.getByTestId('save-button').click();

		await page.waitForURL('/my-profile');

		await page.goto('/analytics');

		// Check that user name display now shows first name and last name instead of email
		await expect(sideBar.userNameDisplay).toHaveText(`${testFirstName} ${testLastName}`);
		//await expect(sideBar.userEmailDisplay).not.toBeVisible();
	});

	await test.step('user profile panel is working properly', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');

		await expect(sideBar.profileButton).toBeVisible();
		await sideBar.profileButton.click();
		await expect(sideBar.morePanel).not.toBeVisible();
		await expect(page).toHaveURL('/my-profile');
		await expect.soft(logedPage.pageTitle).toHaveText('My profile');
	});

	await test.step('docs button is working properly and redirects to gitbook docs', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');

		await expect(sideBar.docsButton).toBeVisible();
	});
});

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
			await sideBar.languageSelect.selectOption(locale);
			await logedPage.hasTitle(m.analytics({}, { locale }));
		}
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');
		await expect(sideBar.languageSelect).toBeVisible();
		setLocale('en');
		await sideBar.languageSelect.selectOption('en');
		await logedPage.hasTitle(m.analytics({}, { locale: 'en' }));
	});
});

test('about panel works properly', async ({ logedPage, sideBar, page }) => {
	await test.step('about panel is working properly', async () => {
		await sideBar.moreButton.click();
		await expect(sideBar.morePanel).not.toHaveAttribute('inert');

		await expect(sideBar.aboutButton).toBeVisible();
		await sideBar.aboutButton.click();
		await expect(logedPage.modalTitle).toBeVisible();
		await expect.soft(logedPage.modalTitle).toHaveText('About CISO Assistant');

		await expect(logedPage.page.getByTestId('version-key')).toContainText('version', {
			ignoreCase: true
		});
		await expect(logedPage.page.getByTestId('version-value')).toBeTruthy();
		await expect(logedPage.page.getByTestId('build-key')).toContainText('build', {
			ignoreCase: true
		});
		await expect(logedPage.page.getByTestId('build-value')).toBeTruthy();
		await page.mouse.click(20, 20); // click outside the modal to close it
		await expect(logedPage.modalTitle).not.toBeVisible();

		await sideBar.logout();
	});
});

import { test as testV2, expect as expectV2 } from '../utilsv2/core/base';

testV2('sidebar component tests', async ({ loginPage }) => {
	await test.step('sidebar can be collapsed and expanded', async () => {
		await loginPage.gotoSelf();
		const analyticsPage = await loginPage.doLoginAdminP();
		await analyticsPage.checkSelf(expectV2);
		await analyticsPage.doCloseModal();

		const sidebar = analyticsPage.getSidebar();
		await sidebar.doToggle();
		await sidebar.checkIsOpened(expectV2);
		await sidebar.doToggle();
		await sidebar.checkIsClosed(expectV2);
	});
});

test('redirect to the right page after login', async ({ loginPage, page }) => {
	await page.goto('/login?next=/calendar');
	await loginPage.hasUrl(1);
	await loginPage.login();
	const currentDate = new Date();
	const year = currentDate.getFullYear();
	const month = currentDate.getMonth() + 1;
	await expect(page).toHaveURL(`/calendar/${year}/${month}`);
});
