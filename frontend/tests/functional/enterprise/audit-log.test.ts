import { test } from '../../utils/test-utils.js';

test('Logging is working properly', async ({ logedPage, auditsLogPage }) => {
	await test.step('original logs show up', async () => {
		await auditsLogPage.goto();
		await auditsLogPage.hasUrl();
	});
});
