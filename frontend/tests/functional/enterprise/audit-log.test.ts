import { test, expect } from '../../utilsv2/core/base';

test('Logs are working properly', async ({ loginPage, auditLogPage }) => {
	await test.step('original logs show up', async () => {
		await loginPage.gotoSelf();
		await loginPage.doLoginAdminP();
		await auditLogPage.gotoSelf();
		await auditLogPage.checkSelf(expect);
		await auditLogPage.doCloseModal();
	});
});
