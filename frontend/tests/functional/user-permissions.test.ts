import { LoginPage } from '../utils/login-page.js';
import { SideBar } from '../utils/sidebar.js';
import { m } from '$paraglide/messages';

import {
	test,
	expect,
	setHttpResponsesListener,
	userFromUserGroupHasPermission,
	TestContent,
	type Page
} from '../utils/test-utils.js';
import testData from '../utils/test-data.js';
import { PageContent } from '../utils/page-content.js';

const userGroups: { string: any } = testData.usergroups;

Object.entries(userGroups).forEach(([userGroup, userGroupData]) => {
	test.describe(`${userGroupData.name} user has the right permissions`, async () => {
		test.describe.configure({ mode: 'serial' });

		const vars = TestContent.generateTestVars();
		const testObjectsData: { [k: string]: any } = TestContent.itemBuilder(vars);

		test.beforeEach(async ({ page }) => {
			setHttpResponsesListener(page);
		});

		test.use({ data: testObjectsData });
		test('user can set his password', async ({
			populateDatabase,
			logedPage,
			usersPage,
			sideBar,
			mailer,
			page
		}) => {
			await usersPage.goto();
			await usersPage.editItemButton(vars.user.email).click();
			await usersPage.form.fill({
				first_name: vars.user.firstName,
				last_name: vars.user.lastName,
				user_groups: [`${vars.folderName} - ${userGroupData.name}`]
			});
			await usersPage.form.saveButton.click();
			await usersPage.isToastVisible(
				'The user: ' + vars.user.email + ' has been successfully updated.+'
			);

			await sideBar.logout();

			await expect(mailer.page.getByText('{{').last()).toBeHidden(); // Wait for mailhog to load the emails
			const lastMail = await mailer.getLastEmail();
			await lastMail.hasWelcomeEmailDetails();
			await lastMail.hasEmailRecipient(vars.user.email);

			await lastMail.open();
			const pagePromise = page.context().waitForEvent('page');
			await expect(mailer.emailContent.setPasswordButton).toBeVisible();
			await mailer.emailContent.setPasswordButton.click();
			const setPasswordPage = await pagePromise;
			await setPasswordPage.waitForLoadState();
			await expect(setPasswordPage).toHaveURL(
				(await mailer.emailContent.setPasswordButton.getAttribute('href')) ||
					'Set password link could not be found'
			);

			const setLoginPage = new LoginPage(setPasswordPage);
			await setLoginPage.newPasswordInput.fill(vars.user.password);
			await setLoginPage.confirmPasswordInput.fill(vars.user.password);
			if (
				setLoginPage.newPasswordInput.inputValue() !== vars.user.password ||
				setLoginPage.confirmPasswordInput.inputValue() !== vars.user.password
			) {
				await setLoginPage.newPasswordInput.fill(vars.user.password);
				await setLoginPage.confirmPasswordInput.fill(vars.user.password);
			}
			await setLoginPage.setPasswordButton.click();

			await setLoginPage.isToastVisible(
				'Your password has been successfully set. Welcome to CISO Assistant!'
			);

			await setLoginPage.login(vars.user.email, vars.user.password);
			await expect(setLoginPage.page).toHaveURL('/analytics');

			// logout to prevent sessions conflicts
			const passwordPageSideBar = new SideBar(setPasswordPage);
			await passwordPageSideBar.logout();
		});

		test.describe(() => {
			let page: Page;

			test.beforeAll(async ({ browser }) => {
				// Create a unique page to use for all the tests on this user group and login
				page = await browser.newPage();
				const loginPage = new LoginPage(page);
				await loginPage.goto();
				await loginPage.login(vars.user.email, vars.user.password);
				await expect(page).toHaveURL('/analytics');
			});

			test.use({
				page: async ({}, use) => {
					await use(page);
				}
			});

			Object.entries(testObjectsData).forEach(([objectPage, objectData], index) => {
				test.describe(`${objectData.displayName.toLowerCase()} permissions`, () => {
					const userCanView = userFromUserGroupHasPermission(
						userGroup,
						'view',
						objectData.modelName ?? objectData.displayName
					);
					const userCanCreate = userFromUserGroupHasPermission(
						userGroup,
						'add',
						objectData.modelName ?? objectData.displayName
					);
					const userCanUpdate = userFromUserGroupHasPermission(
						userGroup,
						'change',
						objectData.modelName ?? objectData.displayName
					);
					const userCanDelete = userFromUserGroupHasPermission(
						userGroup,
						'delete',
						objectData.modelName ?? objectData.displayName
					);

					test.beforeAll(async ({ pages }) => {
						await pages[objectPage].goto();
						await pages[objectPage].waitUntilLoaded();
					});

					test(`${userGroupData.name} user can${
						!userCanView ? ' not' : ''
					} view ${objectData.displayName.toLowerCase()}`, async ({ pages }) => {
						if (
							await pages[objectPage]
								.getRow(objectData.build.name || objectData.build.email || objectData.build.str)
								.isHidden()
						) {
							await pages[objectPage].searchInput.fill(
								objectData.build.name || objectData.build.email || objectData.build.str
							);
						}

						if (userCanView) {
							await expect(
								pages[objectPage].getRow(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeVisible();
						} else {
							await expect(
								pages[objectPage].getRow(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeHidden();
						}
					});

					test(`${userGroupData.name} user can${
						!userCanCreate ? ' not' : ''
					} create ${objectData.displayName.toLowerCase()}`, async ({ pages }) => {
						if (userCanCreate) {
							await expect(pages[objectPage].addButton).toBeVisible();
						} else {
							await expect(pages[objectPage].addButton).toBeHidden();
						}
					});

					test(`${userGroupData.name} user can${
						!userCanUpdate ? ' not' : ''
					} update ${objectData.displayName.toLowerCase()}`, async ({ pages }) => {
						if (
							await pages[objectPage]
								.getRow(objectData.build.name || objectData.build.email || objectData.build.str)
								.isHidden()
						) {
							await pages[objectPage].searchInput.fill(
								objectData.build.name || objectData.build.email || objectData.build.str
							);
						}

						if (userCanUpdate) {
							await expect(
								pages[objectPage].editItemButton(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeVisible();
						} else {
							await expect(
								pages[objectPage].editItemButton(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeHidden();
						}
					});

					test(`${userGroupData.name} user can${
						!userCanDelete ? ' not' : ''
					} delete ${objectData.displayName.toLowerCase()}`, async ({ pages }) => {
						if (
							await pages[objectPage]
								.getRow(objectData.build.name || objectData.build.email || objectData.build.str)
								.isHidden()
						) {
							await pages[objectPage].searchInput.fill(
								objectData.build.name || objectData.build.email || objectData.build.str
							);
						}

						if (userCanDelete) {
							await expect(
								pages[objectPage].deleteItemButton(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeVisible();
						} else {
							await expect(
								pages[objectPage].deleteItemButton(
									objectData.build.name || objectData.build.email || objectData.build.str
								)
							).toBeHidden();
						}
					});
				});
			});
		});

		test.afterAll('cleanup', async ({ browser }) => {
			const page = await browser.newPage();
			const loginPage = new LoginPage(page);
			const usersPage = new PageContent(page, '/users', 'Users');
			const foldersPage = new PageContent(page, '/folders', 'Domains');

			await loginPage.goto();
			await loginPage.login();
			await foldersPage.goto();
			await foldersPage.deleteItemButton(vars.folderName).click();
			await expect(foldersPage.deletePromptConfirmTextField()).toBeVisible();
			await foldersPage.deletePromptConfirmTextField().fill(m.yes());
			await foldersPage.deletePromptConfirmButton().click();
			await expect(foldersPage.getRow(vars.folderName)).not.toBeVisible();
			await usersPage.goto();
			await usersPage.deleteItemButton(vars.user.email).click();
			await usersPage.deleteModalConfirmButton.click();
			await expect(usersPage.getRow(vars.user.email)).not.toBeVisible();
		});
	});
});
