import { test, baseTest, expect } from '../../utils/test-utils.js';

test('every libraries can be imported', async ({
	logedPage,
    librariesPage,
	page
}) => {
	librariesPage.goto();
    librariesPage.hasUrl();
    const librariesRefs = page.locator('tbody tr td:nth-child(1)');
    const libCount = await librariesRefs.count();
    //TODO: make sure that all the the libraries are loaded
    
    for (let i = 0 ; i < libCount ; i++) {
        const libraryRef = await librariesRefs.nth(i).innerText();
        console.log(libraryRef);
        await librariesPage.importLibrary(libraryRef, undefined, 'any');
        await librariesPage.tab('Libraries store').click();
    }
});
