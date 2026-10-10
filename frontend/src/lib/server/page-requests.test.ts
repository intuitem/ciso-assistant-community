import { describe, expect, it } from 'vitest';
import { reachesPage } from './page-requests';

const PAGE_AND_ENDPOINT = '/(app)/[model=internal_urlmodels]';
const ENDPOINT_ONLY = '/(app)/[model=urlmodel]/autocomplete';
const PAGE_ONLY = '/(app)/auditee-dashboard';

const NAVIGATION = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8';

function event(
	routeId: string | null,
	{
		method = 'GET',
		accept,
		action = false,
		isDataRequest = false
	}: { method?: string; accept?: string; action?: boolean; isDataRequest?: boolean }
) {
	const headers = new Headers();
	if (accept) headers.set('accept', accept);
	if (action) headers.set('x-sveltekit-action', 'true');
	return {
		route: { id: routeId },
		request: new Request('http://localhost/', { method, headers }),
		isDataRequest
	} as Parameters<typeof reachesPage>[0];
}

describe('reachesPage follows SvelteKit dispatch', () => {
	it.each([
		['a navigation', { accept: NAVIGATION }, true],
		['its data', { isDataRequest: true }, true],
		['an enhanced form action', { method: 'POST', action: true }, true],
		['a plain form post', { method: 'POST', accept: NAVIGATION }, true],
		['a fetch', {}, false],
		['a JSON fetch', { accept: 'application/json' }, false],
		['a fetch posting JSON', { method: 'POST', accept: 'application/json' }, false],
		['a delete', { method: 'DELETE', accept: NAVIGATION }, false],
		// kit only weighs html against */*, so html wins over a preferred json here...
		['html after json', { accept: 'application/json, text/html;q=0.1' }, true],
		// ...and loses to a wildcard ranked first.
		['html after a wildcard', { accept: '*/*, text/html;q=0.5' }, false]
	])('on a page with an endpoint: %s', (_, init, expected) => {
		expect(reachesPage(event(PAGE_AND_ENDPOINT, init))).toBe(expected);
	});

	it('a page without an endpoint answers fetches too', () => {
		expect(reachesPage(event(PAGE_ONLY, {}))).toBe(true);
	});

	it('an endpoint without a page never reaches one', () => {
		expect(reachesPage(event(ENDPOINT_ONLY, { accept: NAVIGATION }))).toBe(false);
		expect(reachesPage(event(ENDPOINT_ONLY, { method: 'POST', action: true }))).toBe(false);
	});

	it('an unmatched path reaches no page', () => {
		expect(reachesPage(event(null, { accept: NAVIGATION }))).toBe(false);
	});
});
