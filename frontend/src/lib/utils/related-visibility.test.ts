import { describe, it, expect, vi } from 'vitest';
import { findHiddenIds } from '#lib/utils/related-visibility.js';

function serving(rows: { id: string }[], ok = true) {
	return vi.fn(async (_url: string) => ({
		ok,
		status: ok ? 200 : 500,
		statusText: ok ? 'OK' : 'Server Error',
		body: null,
		json: async () => ({ count: rows.length, next: null, results: rows })
	})) as unknown as typeof fetch & ReturnType<typeof vi.fn>;
}

describe('findHiddenIds', () => {
	it('reports the ids the endpoint does not return', async () => {
		const fetchFn = serving([{ id: 'seen' }]);
		expect(await findHiddenIds(fetchFn, 'evidences', ['seen', 'hidden'])).toEqual(['hidden']);
	});

	it("ignores the picker's filters, so a filtered-out object is not hidden", async () => {
		const fetchFn = serving([{ id: 'other-scope' }]);
		const hidden = await findHiddenIds(fetchFn, 'evidences?folder=abc', ['other-scope']);
		expect(hidden).toEqual([]);
		const url = String(fetchFn.mock.calls[0][0]);
		expect(url.startsWith('/evidences?id=other-scope')).toBe(true);
		expect(url).not.toContain('folder=');
	});

	it('keeps every id when the lookup fails, so none is dropped on save', async () => {
		const fetchFn = serving([], false);
		expect(await findHiddenIds(fetchFn, 'evidences', ['a', 'b'])).toEqual(['a', 'b']);
	});

	it('does not fetch without ids', async () => {
		const fetchFn = serving([]);
		expect(await findHiddenIds(fetchFn, 'evidences', [])).toEqual([]);
		expect(fetchFn).not.toHaveBeenCalled();
	});
});
