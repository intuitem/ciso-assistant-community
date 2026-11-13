import { describe, it, expect, vi } from 'vitest';
import { fetchNeighbour } from '#lib/utils/taskOccurrences.js';

function serving(rows: { id: string; due_date: string }[]) {
	return vi.fn(async () => ({
		ok: true,
		json: async () => ({
			count: rows.length,
			results: rows.map((r) => ({ ...r, status: 'pending' }))
		})
	})) as unknown as typeof fetch;
}

describe('fetchNeighbour', () => {
	const current = { id: 'b', dueDate: '2026-03-01' };

	it('reaches an occurrence due the same day', async () => {
		const fetchFn = serving([
			{ id: 'b', due_date: '2026-03-01' },
			{ id: 'c', due_date: '2026-03-01' },
			{ id: 'z', due_date: '2026-04-01' }
		]);
		const { occurrence } = await fetchNeighbour(fetchFn, 't', current, false);
		expect(occurrence?.id).toBe('c');
	});

	it('goes back past same-day occurrences that come after', async () => {
		const fetchFn = serving([
			{ id: 'c', due_date: '2026-03-01' },
			{ id: 'b', due_date: '2026-03-01' },
			{ id: 'a', due_date: '2026-03-01' }
		]);
		const { occurrence } = await fetchNeighbour(fetchFn, 't', current, true);
		expect(occurrence?.id).toBe('a');
	});

	it('moves to another day when the current one is the last of its day', async () => {
		const fetchFn = serving([
			{ id: 'b', due_date: '2026-03-01' },
			{ id: 'a', due_date: '2026-04-01' }
		]);
		const { occurrence } = await fetchNeighbour(fetchFn, 't', current, false);
		expect(occurrence?.id).toBe('a');
	});
});
