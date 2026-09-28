import { test, expect } from '../../utils/test-utils.js';

// Regression test for the /undefined request: the preview tables on a library
// detail page are fed from the library payload and get no URLModel, so
// ModelTable used to build the endpoint `/undefined`, fetch it, fail with a 404
// and replace the rows it had been given with an empty list.
test('library preview table renders its rows without any remote request', async ({
	logedPage,
	page
}) => {
	const strayRequests: string[] = [];
	page.on('request', (request) => {
		if (request.url().includes('/undefined')) strayRequests.push(request.url());
	});

	// A library whose only listed objects are reference controls: its detail page
	// renders exactly one preview table, so the row count is unambiguous.
	const libraries = await page.request
		.get('/stored-libraries?limit=1000')
		.then((res) => res.json());
	const library = (libraries.results ?? []).find((lib: Record<string, any>) => {
		const meta = lib.objects_meta ?? {};
		return meta.reference_controls > 0 && Object.keys(meta).length === 1;
	});
	test.skip(!library, 'no stored library exposing only reference controls in this database');

	await page.goto(`/stored-libraries/${library.id}`);
	await expect(page).toHaveURL(/.*stored-libraries.*/);
	// The rows were briefly there before being replaced, so let the page settle
	// first: the assertion below has to describe the state that lasts.
	await page.waitForLoadState('networkidle');

	expect(strayRequests).toEqual([]);
	await expect(page.locator('table tbody tr')).toHaveCount(library.objects_meta.reference_controls);
});
