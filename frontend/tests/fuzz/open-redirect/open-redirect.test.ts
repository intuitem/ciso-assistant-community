import { expect, test } from '../../utils/test-utils.js';

import { readFileSync } from 'fs';

test('open redirect fuzz tests', async ({ logedPage }) => {
	await test.step('fuzz open redirect', async () => {
		await logedPage.page.getByRole('button', { name: 'Organization' }).click();
		await logedPage.page.getByTestId('accordion-item-folders').click();
		await logedPage.page.getByTestId('add-button').click();
		await logedPage.page
			.getByTestId('form-input-name')
			.fill('Irure commodo consequat fugiat elit mollit in aute et incididunt et tempor.');
		await logedPage.page.getByTestId('save-button').click();

		const payloadsFile = './tests/fuzz/open-redirect/payloads.txt';
		const payloads = readFileSync(payloadsFile, 'utf8').split('\n');

		const href = await logedPage.page
			.getByTestId('tablerow-edit-button')
			.getAttribute('href')
			.then((href) => href!.split('?')[0]);

		const currentURL = logedPage.page.url();
		const parsedURL = new URL(currentURL);
		const hostname = parsedURL.hostname;

		for (const payload of payloads) {
			await logedPage.page.goto(`${href}?next=${payload}`);
			await logedPage.page.getByTestId('cancel-button').click();
			// Redirecting to next MUST not redirect to another domain
			await expect(logedPage.page).toHaveURL(new RegExp(`^.*${hostname}.*$`));
		}
	});
});
