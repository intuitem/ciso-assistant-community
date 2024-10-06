import { expect, setHttpResponsesListener, test } from '../../utils/test-utils.js';

import { readFileSync } from 'fs';

test('open redirect fuzz tests', async () => {
	test.slow();

	await test.step('fuzz open redirect', async () => {
		const payloadsFile = './tests/fuzz/open-redirect/payloads.txt';
		const payloads = readFileSync(payloadsFile, 'utf8').split('\n');
		console.log(payloads);
	});
});
