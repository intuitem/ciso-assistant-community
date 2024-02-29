import { test, expect } from '../../utils/test-utils.js';

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
