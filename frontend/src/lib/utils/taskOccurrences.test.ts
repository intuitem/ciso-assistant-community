import { describe, it, expect, vi } from 'vitest';
import { fetchNeighbour, fetchOccurrenceHistory } from '#lib/utils/taskOccurrences.js';

function serving(rows: { id: string; due_date: string }[]) {
	return vi.fn(async (_url: string) => ({
		ok: true,
		json: async () => ({
			count: rows.length,
			results: rows.map((r) => ({ ...r, status: 'pending' }))
		})
	}));
}

/** The query string of the only request made. */
function queryOf(fetchFn: ReturnType<typeof serving>) {
	expect(fetchFn).toHaveBeenCalledTimes(1);
	const url = new URL(fetchFn.mock.calls[0][0], 'http://localhost');
	return Object.fromEntries(url.searchParams);
}

describe('fetchNeighbour', () => {
	it('asks for the one occurrence due just after the date', async () => {
		const fetchFn = serving([{ id: 'c', due_date: '2026-04-01' }]);
		const found = await fetchNeighbour(
			fetchFn as unknown as typeof fetch,
			't',
			'2026-03-01',
			false
		);
		expect(found).toMatchObject({ occurrence: { id: 'c' }, failed: false });
		expect(queryOf(fetchFn)).toEqual({
			task_template: 't',
			due_date__gt: '2026-03-01',
			ordering: 'due_date',
			limit: '1'
		});
	});

	it('asks for the one occurrence due just before the date', async () => {
		const fetchFn = serving([{ id: 'a', due_date: '2026-02-01' }]);
		const found = await fetchNeighbour(fetchFn as unknown as typeof fetch, 't', '2026-03-01', true);
		expect(found).toMatchObject({ occurrence: { id: 'a' }, failed: false });
		expect(queryOf(fetchFn)).toEqual({
			task_template: 't',
			due_date__lt: '2026-03-01',
			ordering: '-due_date',
			limit: '1'
		});
	});

	it('has no neighbour past the first or the last occurrence', async () => {
		const fetchFn = serving([]);
		const found = await fetchNeighbour(
			fetchFn as unknown as typeof fetch,
			't',
			'2026-03-01',
			false
		);
		expect(found).toEqual({ occurrence: null, failed: false });
	});
});

describe('fetchOccurrenceHistory', () => {
	interface Window {
		/** The server's total, which the window may not hold in full. */
		count: number;
		/** Due dates, in the order the server returns them. */
		dates: string[];
	}

	/** Answers the past and the upcoming request, each with its own window. */
	function servingWindows(windows: { past: Window; upcoming: Window }) {
		return vi.fn(async (url: string) => {
			const isPast = new URL(url, 'http://localhost').searchParams.get('past') === 'true';
			const { count, dates } = isPast ? windows.past : windows.upcoming;
			const results = dates.map((due_date) => ({ id: due_date, due_date, status: 'pending' }));
			return { ok: true, json: async () => ({ count, results }) };
		});
	}

	const datesOf = (occurrences: { due_date: string | null }[]) =>
		occurrences.map((occurrence) => occurrence.due_date);

	it('keeps a window that holds every occurrence', async () => {
		const past = ['2026-03-04', '2026-02-25', '2026-02-18'];
		const upcoming = ['2026-03-11', '2026-03-18'];
		const history = await fetchOccurrenceHistory(
			servingWindows({
				past: { count: 3, dates: past },
				upcoming: { count: 2, dates: upcoming }
			}) as unknown as typeof fetch,
			't'
		);
		expect(datesOf(history.pastOccurrences)).toEqual(past);
		expect(datesOf(history.upcomingOccurrences)).toEqual(upcoming);
	});

	it('leaves out the month a full window is cut in', async () => {
		const history = await fetchOccurrenceHistory(
			servingWindows({
				// Newest first: older occurrences exist, so February may be cut.
				past: { count: 9, dates: ['2026-03-04', '2026-02-25', '2026-02-18'] },
				// Oldest first: later occurrences exist, so April may be cut.
				upcoming: { count: 9, dates: ['2026-03-11', '2026-03-18', '2026-04-01'] }
			}) as unknown as typeof fetch,
			't'
		);
		expect(datesOf(history.pastOccurrences)).toEqual(['2026-03-04']);
		expect(datesOf(history.upcomingOccurrences)).toEqual(['2026-03-11', '2026-03-18']);
		// What is counted is what the server holds, not what the history shows.
		expect(history.upcomingCount).toBe(9);
	});
});
