import { test, expect } from '../../utils/test-utils.js';

test.describe.configure({ mode: 'serial' });
test('every libraries can be imported', async ({
	logedPage,
    librariesPage,
	page
}) => {
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
        if (await page.locator('tbody tr td:nth-child(1)').count() !== 0) {
            nextRemainingLibrary = await page.locator('tbody tr td:nth-child(1)').first()?.innerText();
        }
        else {
            break;    
        }
        expect(previousRemainingLibrary, "An error occured while importing library: " + previousRemainingLibrary).not.toEqual(nextRemainingLibrary);
    }
});

test('every libraries can be deleted', async ({
    logedPage,
    librariesPage,
    page
}) => {
    test.fail(true, "This test is currently failing due to a bug with delete buttons and dependencies. Check JIRA for more information.");
    test.slow();
    await librariesPage.goto();
    await librariesPage.hasUrl();
    
    await expect(librariesPage.tab('Imported libraries'), "There is no imported libraries to delete").toBeVisible();
    if (await librariesPage.tab('Imported libraries').isVisible() && await librariesPage.tab('Imported libraries').getAttribute('aria-selected') === 'false') {
        await librariesPage.tab('Imported libraries').click();
        expect(librariesPage.tab('Imported libraries').getAttribute('aria-selected')).toBeTruthy();
    }

    let previousRemainingLibrary = '';
    let nextRemainingLibrary = '';
    let count = 0;
    do {
        if (await librariesPage.tab('Imported libraries').isVisible()) {
            previousRemainingLibrary = nextRemainingLibrary;
            nextRemainingLibrary = await page.locator('tbody tr td:nth-child(1)').nth(count)?.innerText();
            expect(previousRemainingLibrary, "An error occured while deleting library: " + previousRemainingLibrary).not.toEqual(nextRemainingLibrary);
        }
        else {
            break;    
        }
        
        if (await librariesPage.deleteItemButton(nextRemainingLibrary).isVisible()) {
            await librariesPage.deleteItemButton(nextRemainingLibrary).click();
            await librariesPage.deleteModalConfirmButton.click();
		    await librariesPage.isToastVisible('Successfully deleted.+', undefined, {
                timeout: 15000
            });
            await expect(librariesPage.getRow(nextRemainingLibrary)).not.toBeVisible();
            count = 0;
        }
        else {
            count++;
            continue;
        }
        // const toast = page.getByTestId('toast').first();
		// await toast.getByLabel('Dismiss toast').click();
		// await expect(toast).toBeHidden();
        
    } while (nextRemainingLibrary);
});