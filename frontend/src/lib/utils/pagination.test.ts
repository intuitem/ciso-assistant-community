import { describe, it, expect, vi } from 'vitest';

import { fetchAllByIds, fetchAllPages } from './pagination';

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

	it('throws instead of returning a silent partial when maxPages is exhausted', async () => {
		// Server keeps claiming there is a next page.
		const fetchFn = vi.fn(async () =>
			jsonResponse({ count: 100, next: 'more', previous: null, results: [1] })
		) as unknown as typeof fetch;
		await expect(fetchAllPages(fetchFn, '/assets', { maxPages: 3 })).rejects.toThrow(
			'aborted after 3 pages'
		);
	});
});

describe('fetchAllByIds', () => {
	it('chunks the id list and merges the hydrated rows', async () => {
		const requested: string[] = [];
		const fetchFn = vi.fn(async (url: string | URL | Request) => {
			requested.push(String(url));
			const params = new URL(String(url), 'http://x').searchParams;
			const ids = (params.get('id') ?? '').split(',');
			return jsonResponse({ count: ids.length, next: null, previous: null, results: ids });
		}) as unknown as typeof fetch;

		const ids = Array.from({ length: 5 }, (_, i) => `id-${i}`);
		const rows = await fetchAllByIds<string>(fetchFn, '/assets/autocomplete', ids, {
			chunkSize: 2
		});
		expect(rows).toEqual(ids);
		expect(fetchFn).toHaveBeenCalledTimes(3);
		expect(requested[0]).toBe('/assets/autocomplete?id=id-0%2Cid-1&limit=200');
	});

	it('pages inside a chunk when the server paginates the hydration', async () => {
		// One chunk of 3 ids served one row per page.
		const fetchFn = vi.fn(async (url: string | URL | Request) => {
			const params = new URL(String(url), 'http://x').searchParams;
			const ids = (params.get('id') ?? '').split(',');
			const offset = Number(params.get('offset') ?? 0);
			const results = ids.slice(offset, offset + 1);
			return jsonResponse({
				count: ids.length,
				next: offset + 1 < ids.length ? 'more' : null,
				previous: null,
				results
			});
		}) as unknown as typeof fetch;

		const rows = await fetchAllByIds<string>(fetchFn, '/assets/autocomplete', ['a', 'b', 'c']);
		expect(rows).toEqual(['a', 'b', 'c']);
		expect(fetchFn).toHaveBeenCalledTimes(3);
	});

	it('appends the id param to a url that already has a query string', async () => {
		const requested: string[] = [];
		const fetchFn = vi.fn(async (url: string | URL | Request) => {
			requested.push(String(url));
			return jsonResponse({ count: 0, next: null, previous: null, results: [] });
		}) as unknown as typeof fetch;

		await fetchAllByIds(fetchFn, '/folders/autocomplete?content_type=DO', ['x']);
		expect(requested[0]).toBe('/folders/autocomplete?content_type=DO&id=x&limit=200');
	});
});
