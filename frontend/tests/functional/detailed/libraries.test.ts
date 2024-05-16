import { test, expect } from '../../utils/test-utils.js';

test.describe.configure({ mode: 'serial' });
test('every libraries can be loaded', async ({ logedPage, librariesPage, page }) => {
	test.slow();
	await librariesPage.goto();
	await librariesPage.hasUrl();

	let previousRemainingLibrary = '';
	let nextRemainingLibrary = await page.locator('tbody tr td:nth-child(1)').first()?.innerText();
	while (nextRemainingLibrary) {
		await librariesPage.importLibrary(nextRemainingLibrary, undefined, 'any');

		await librariesPage.tab('Libraries store').click();
		expect(librariesPage.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();

		previousRemainingLibrary = nextRemainingLibrary;
		if ((await page.locator('tbody tr td:nth-child(1)').count()) !== 0) {
			nextRemainingLibrary = await page.locator('tbody tr td:nth-child(1)').first()?.innerText();
		} else {
			break;
		}
		expect(
			previousRemainingLibrary,
			'An error occured while importing library: ' + previousRemainingLibrary
		).toEqual(nextRemainingLibrary);
	}
});

test('every libraries can be deleted', async ({ logedPage, librariesPage, page }) => {
	test.slow();
	test.skip(
		true,
		'This test is skipped because of an issue with delete button not being visible with dependencies in CI'
	);

	await librariesPage.goto();
	await librariesPage.hasUrl();

	await expect(
		librariesPage.tab('Loaded libraries'),
		'There is no loaded libraries to delete'
	).toBeVisible();
	if (
		(await librariesPage.tab('Loaded libraries').isVisible()) &&
		(await librariesPage.tab('Loaded libraries').getAttribute('aria-selected')) === 'false'
	) {
		await librariesPage.tab('Loaded libraries').click();
		expect(librariesPage.tab('Loaded libraries').getAttribute('aria-selected')).toBeTruthy();
	}

	let previousRemainingLibrary = '';
	let nextRemainingLibrary = '';
	let count = 0;
	do {
		await page.reload(); // this is a workaround to try to fix the issue with delete button not being visible with dependencies in CI
		if (await librariesPage.tab('Loaded libraries').isVisible()) {
			previousRemainingLibrary = nextRemainingLibrary;
			nextRemainingLibrary = await page.locator('tbody tr td:nth-child(1)').nth(count)?.innerText();
			expect(
				previousRemainingLibrary,
				'An error occured while deleting library: ' + previousRemainingLibrary
			).not.toEqual(nextRemainingLibrary);
		} else {
			break;
		}

		if (await librariesPage.deleteItemButton(nextRemainingLibrary).isVisible()) {
			await librariesPage.deleteItemButton(nextRemainingLibrary).click();
			await librariesPage.deleteModalConfirmButton.click();
			await librariesPage.isToastVisible(
				'The library object has been successfully deleted.+',
				undefined,
				{
					timeout: 15000
				}
			);
			if (await page.getByText(' You currently have no loaded libraries.').isHidden()) {
				await expect(librariesPage.getRow(nextRemainingLibrary)).not.toBeVisible();
			} else {
				break;
			}
			count = 0;
		} else {
			count++;
			continue;
		}
	} while (
		nextRemainingLibrary ||
		(await page.getByText(' You currently have no loaded libraries.').isHidden())
	);
});
