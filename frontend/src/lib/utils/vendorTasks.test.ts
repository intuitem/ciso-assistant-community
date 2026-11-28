import { describe, expect, it, vi } from 'vitest';
import { fetchVendorAssignees } from './vendorTasks';

const enclave = { id: 'enclave-a', content_type: 'EN' };

function respondWith(body: unknown, ok = true): typeof globalThis.fetch {
	return vi.fn(async () => ({ ok, json: async () => body }) as Response);
}

describe('fetchVendorAssignees', () => {
	it("prefills a reviewer's task with the preferred respondents only", async () => {
		const fetch = respondWith({ results: [{ id: 'alice' }] });

		expect(await fetchVendorAssignees(fetch, enclave, false)).toEqual(['alice']);
		expect(fetch).toHaveBeenCalledOnce();
		expect(vi.mocked(fetch).mock.calls[0][0]).toContain(
			'/actors/?respondents_of=enclave-a&respondents_only=true&preferred_only=true'
		);
	});

	it('prefills every workspace respondent when none is preferred', async () => {
		const pages = [{ results: [] }, { results: [{ id: 'alice' }, { id: 'carol' }] }];
		const fetch = vi.fn(async () => ({ ok: true, json: async () => pages.shift() }) as Response);

		expect(await fetchVendorAssignees(fetch, enclave, false)).toEqual(['alice', 'carol']);
		expect(vi.mocked(fetch).mock.calls[1][0]).not.toContain('preferred_only');
	});

	it('prefills nothing outside an enclave, for a vendor, or without a folder', async () => {
		const fetch = respondWith({ results: [{ id: 'alice' }] });

		expect(await fetchVendorAssignees(fetch, { id: 'domain', content_type: 'DO' }, false)).toEqual(
			[]
		);
		expect(await fetchVendorAssignees(fetch, enclave, true)).toEqual([]);
		expect(await fetchVendorAssignees(fetch, undefined, false)).toEqual([]);
		expect(fetch).not.toHaveBeenCalled();
	});

	it('prefills nothing when the lookup fails', async () => {
		expect(await fetchVendorAssignees(respondWith({}, false), enclave, false)).toEqual([]);
	});

	it('prefills nothing, without failing the page, when the request throws', async () => {
		const fetch = vi.fn(async () => {
			throw new TypeError('fetch failed');
		});

		expect(await fetchVendorAssignees(fetch, enclave, false)).toEqual([]);
	});

	it('prefills the preferred respondents of every page', async () => {
		const pages = [
			{ results: [{ id: 'alice' }], next: 'page-2' },
			{ results: [{ id: 'carol' }], next: null }
		];
		const fetch = vi.fn(async () => ({ ok: true, json: async () => pages.shift() }) as Response);

		expect(await fetchVendorAssignees(fetch, enclave, false)).toEqual(['alice', 'carol']);
	});
});
