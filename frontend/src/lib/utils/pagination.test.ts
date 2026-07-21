import { describe, it, expect, vi } from 'vitest';

import { fetchAllPages } from './pagination';

function jsonResponse(body: unknown, ok = true, status = 200) {
	return {
		ok,
		status,
		statusText: ok ? 'OK' : 'Server Error',
		json: async () => body
	} as unknown as Response;
}

function paginatedFetch(rows: number[], pageSize: number) {
	// Simulates the backend envelope: pages of `pageSize`, next=null at the end.
	return vi.fn(async (url: string | URL | Request) => {
		const params = new URL(String(url), 'http://x').searchParams;
		const offset = Number(params.get('offset') ?? 0);
		const limit = Number(params.get('limit') ?? pageSize);
		const results = rows.slice(offset, offset + Math.min(limit, pageSize));
		return jsonResponse({
			count: rows.length,
			next: offset + results.length < rows.length ? 'ignored' : null,
			previous: null,
			results
		});
	}) as unknown as typeof fetch;
}

describe('fetchAllPages', () => {
	it('concatenates every page until next is null', async () => {
		const rows = Array.from({ length: 12 }, (_, i) => i);
		const fetchFn = paginatedFetch(rows, 5);
		const all = await fetchAllPages<number>(fetchFn, '/assets/autocomplete?id=a,b');
		expect(all).toEqual(rows);
		expect(fetchFn).toHaveBeenCalledTimes(3);
	});

	it('requests the max page size by default', async () => {
		const fetchFn = paginatedFetch([1, 2], 500);
		await fetchAllPages(fetchFn, '/assets?folder=f1');
		expect(fetchFn).toHaveBeenNthCalledWith(1, '/assets?folder=f1&limit=200');
		const fetchFn2 = paginatedFetch([1, 2], 500);
		await fetchAllPages(fetchFn2, '/assets');
		expect(fetchFn2).toHaveBeenNthCalledWith(1, '/assets?limit=200');
	});

	it('pages with explicit offsets on subsequent requests', async () => {
		const rows = Array.from({ length: 7 }, (_, i) => i);
		const fetchFn = paginatedFetch(rows, 3);
		await fetchAllPages(fetchFn, '/assets?folder=f1', { pageSize: 3 });
		expect(fetchFn).toHaveBeenNthCalledWith(2, '/assets?folder=f1&offset=3&limit=3');
		expect(fetchFn).toHaveBeenNthCalledWith(3, '/assets?folder=f1&offset=6&limit=3');
	});

	it('honors an explicit pageSize option', async () => {
		const rows = Array.from({ length: 4 }, (_, i) => i);
		const fetchFn = paginatedFetch(rows, 100);
		await fetchAllPages(fetchFn, '/assets', { pageSize: 2 });
		expect(fetchFn).toHaveBeenNthCalledWith(1, '/assets?limit=2');
		expect(fetchFn).toHaveBeenNthCalledWith(2, '/assets?offset=2&limit=2');
	});

	it('returns plain-array responses as-is', async () => {
		const fetchFn = vi.fn(async () => jsonResponse([1, 2, 3])) as unknown as typeof fetch;
		const all = await fetchAllPages<number>(fetchFn, '/folders/org_tree');
		expect(all).toEqual([1, 2, 3]);
		expect(fetchFn).toHaveBeenCalledTimes(1);
	});

	it('throws on a failed response', async () => {
		const fetchFn = vi.fn(async () => jsonResponse({}, false, 500)) as unknown as typeof fetch;
		await expect(fetchAllPages(fetchFn, '/assets')).rejects.toThrow('500');
	});

	it('stops on an empty page even if next is set', async () => {
		const fetchFn = vi.fn(async () =>
			jsonResponse({ count: 10, next: 'stale', previous: null, results: [] })
		) as unknown as typeof fetch;
		const all = await fetchAllPages(fetchFn, '/assets');
		expect(all).toEqual([]);
		expect(fetchFn).toHaveBeenCalledTimes(1);
	});
});
