import { expect, test, TestContent } from '../../utils/test-utils.js';

test.describe('Exceptions page CRUD', () => {
	test.slow();
	const testContent = TestContent.itemBuilder();
	const exception = testContent.securityExceptionsPage;
	const domain = testContent.foldersPage;

	test.beforeEach(async ({ logedPage, foldersPage, securityExceptionsPage }) => {
		//Before each but could be used only once for "can create a new exception"
		await foldersPage.goto();
		await foldersPage.waitUntilLoaded();
		await foldersPage.waitUntilTableLoaded();
		
		const row = foldersPage.getRow(domain.build.name);
		if (!(await row.isVisible())) {
			await foldersPage.createItem(domain.build);
		}

		await securityExceptionsPage.goto();
	});

	test('can create a new exception', async ({ securityExceptionsPage }) => {
		await test.step('Create a new exception', async () => {
			await securityExceptionsPage.createItem(exception.build);
		});

		await test.step('Verify the exception has been created', async () => {
			await securityExceptionsPage.getRow(exception.build.name).waitFor();
			const row = securityExceptionsPage.getRow(exception.build.name);
			await expect(row).toBeVisible();
		});
	});

	test('can view an exception details', async ({ securityExceptionsPage }) => {

		await test.step('Navigate to exception details', async () => {
			await securityExceptionsPage.viewItemDetail(exception.build.name);
			await securityExceptionsPage.itemDetail.hasTitle(exception.build.name);
		});

		await test.step('Verify exception details', async () => {
			await securityExceptionsPage.itemDetail.verifyItem(exception.build);
		});
	});

	test('can edit an existing exception', async ({ securityExceptionsPage }) => {
       await securityExceptionsPage.waitUntilTableLoaded();
       
       await test.step('Edit the exception', async () => {
           // Recreated the process to avoid issue with "editItem" methode
           await securityExceptionsPage.editItemButton(exception.build.name).click();
           
           await securityExceptionsPage.itemDetail.hasBreadcrumbPath(['Edit'], false);

           const editedValues: { [k: string]: any } = {};
           for (const key in exception.editParams) {
               editedValues[key] =
                   exception.editParams[key] === ''
                       ? exception.build[key] + ' edited'
                       : exception.editParams[key];
           }

           await securityExceptionsPage.form.fill(editedValues);
           await securityExceptionsPage.form.saveButton.click();
           
           await securityExceptionsPage.isToastVisible('The .+ has been successfully updated');
           
           Object.assign(exception.build, editedValues);
       });

       await test.step('Verify the exception has been edited', async () => {
           await securityExceptionsPage.viewItemDetail(exception.build.name);
           await securityExceptionsPage.itemDetail.verifyItem(exception.build);
       });
   });

	test('can delete an exception', async ({ securityExceptionsPage, page }) => {

		await test.step('Delete the exception', async () => {
			await securityExceptionsPage.deleteItemButton(exception.build.name).click();
			await expect(securityExceptionsPage.deleteModalTitle).toBeVisible();
			await securityExceptionsPage.deleteModalConfirmButton.click();
			await securityExceptionsPage.isToastVisible('The exception object has been successfully deleted');
		});

		await test.step('Verify the exception has been deleted', async () => {
			await page.waitForTimeout(1000);
			await expect(securityExceptionsPage.getRow(exception.build.name)).not.toBeVisible();
		});
	});
});