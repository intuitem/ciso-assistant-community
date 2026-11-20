import { describe, expect, it, vi } from 'vitest';
import { fetchVendorAssignees } from './vendorTasks';

const enclave = { id: 'enclave-a', content_type: 'EN' };

function respondWith(body: unknown, ok = true): typeof globalThis.fetch {
	return vi.fn(async () => ({ ok, json: async () => body }) as Response);
}

describe('fetchVendorAssignees', () => {
	it("prefills a reviewer's task with the workspace respondents", async () => {
		const fetch = respondWith({ results: [{ id: 'alice' }, { id: 'carol' }] });

		expect(await fetchVendorAssignees(fetch, enclave, false)).toEqual(['alice', 'carol']);
		expect(vi.mocked(fetch).mock.calls[0][0]).toContain(
			'/actors/?respondents_of=enclave-a&respondents_only=true'
		);
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
});
