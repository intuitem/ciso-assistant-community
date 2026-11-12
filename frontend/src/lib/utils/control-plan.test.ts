import { describe, expect, it } from 'vitest';
import {
	clampPaneWidth,
	defaultViewSettings,
	flattenTasks,
	groupRows,
	moveColumn,
	parseViewSettings,
	schedulePeriodDays,
	sortRows,
	type ReviewTask,
	type TaskRow,
	isOutstanding,
	isCurrentBucket,
	isGranularity,
	localIsoDate,
	monthBands,
	orderWindow,
	rollingWindow,
	sameWindow,
	yearWindow
} from './control-plan';

// Month index is 0-based in the Date constructor: 10 = November.
const NOV_11 = new Date(2026, 10, 11);

describe('rollingWindow', () => {
	it('shows 2 months back and 9 ahead in monthly view', () => {
		expect(rollingWindow(NOV_11, 'monthly')).toEqual({
			startYear: 2026,
			startMonth: 9,
			endYear: 2027,
			endMonth: 8
		});
	});

	it('crosses the year backwards in January', () => {
		expect(rollingWindow(new Date(2026, 0, 15), 'monthly')).toEqual({
			startYear: 2025,
			startMonth: 11,
			endYear: 2026,
			endMonth: 10
		});
	});

	it('rounds 2 weeks back and 9 ahead out to whole months in weekly view', () => {
		// 2 weeks before 11 Nov is 28 Oct; 9 weeks after is 13 Jan.
		expect(rollingWindow(NOV_11, 'weekly')).toEqual({
			startYear: 2026,
			startMonth: 10,
			endYear: 2027,
			endMonth: 1
		});
	});

	it('stays within the month when 2 weeks back does not leave it', () => {
		const window = rollingWindow(new Date(2026, 10, 20), 'weekly');
		expect([window.startYear, window.startMonth]).toEqual([2026, 11]);
	});

	it('shows 1 quarter back and 3 ahead in quarterly view', () => {
		// Current quarter is Q4 2026: from Q3 2026 to Q3 2027.
		expect(rollingWindow(NOV_11, 'quarterly')).toEqual({
			startYear: 2026,
			startMonth: 7,
			endYear: 2027,
			endMonth: 9
		});
	});

	it('shows 1 semester back and 2 ahead in semiannual view', () => {
		// Current semester is H2 2026: from H1 2026 to H2 2027.
		expect(rollingWindow(NOV_11, 'semiannual')).toEqual({
			startYear: 2026,
			startMonth: 1,
			endYear: 2027,
			endMonth: 12
		});
	});
});

describe('yearWindow / sameWindow', () => {
	it('covers January to December', () => {
		expect(yearWindow(2026)).toEqual({
			startYear: 2026,
			startMonth: 1,
			endYear: 2026,
			endMonth: 12
		});
	});

	it('compares every bound', () => {
		expect(sameWindow(yearWindow(2026), yearWindow(2026))).toBe(true);
		expect(sameWindow(yearWindow(2026), { ...yearWindow(2026), endMonth: 11 })).toBe(false);
	});
});

describe('isCurrentBucket', () => {
	const today = localIsoDate(NOV_11);

	it('formats the local date', () => {
		expect(today).toBe('2026-11-11');
		expect(localIsoDate(new Date(2026, 0, 5))).toBe('2026-01-05');
	});

	it('includes both bounds', () => {
		expect(isCurrentBucket({ start: '2026-11-01', end: '2026-11-30' }, today)).toBe(true);
		expect(isCurrentBucket({ start: '2026-11-11', end: '2026-11-11' }, today)).toBe(true);
		expect(isCurrentBucket({ start: '2026-11-09', end: '2026-11-15' }, today)).toBe(true);
	});

	it('excludes other periods', () => {
		expect(isCurrentBucket({ start: '2026-10-01', end: '2026-10-31' }, today)).toBe(false);
		expect(isCurrentBucket({ start: '2026-11-12', end: '2026-11-18' }, today)).toBe(false);
	});
});

describe('monthBands', () => {
	it('groups week columns under the month they start in', () => {
		const weeks = ['2026-10-01', '2026-10-05', '2026-10-26', '2026-11-02', '2027-01-04'].map(
			(start) => ({ start })
		);
		expect(monthBands(weeks)).toEqual([
			{ key: '2026-10', year: 2026, month: 10, span: 3 },
			{ key: '2026-11', year: 2026, month: 11, span: 1 },
			{ key: '2027-01', year: 2027, month: 1, span: 1 }
		]);
	});

	it('returns nothing for no buckets', () => {
		expect(monthBands([])).toEqual([]);
	});
});

describe('isGranularity', () => {
	it('accepts the four granularities only', () => {
		expect(isGranularity('quarterly')).toBe(true);
		expect(isGranularity('semiannual')).toBe(true);
		expect(isGranularity('daily')).toBe(false);
		expect(isGranularity(null)).toBe(false);
	});
});

describe('isOutstanding', () => {
	const bucket = (status: string | null, overdue: boolean) => ({ status, node_ids: [], overdue });
	const task = (bucket_status: Record<string, ReturnType<typeof bucket>>) => ({ bucket_status });

	it('flags an overdue occurrence in any period', () => {
		expect(isOutstanding(task({ '2026-09': bucket('pending', true) }), '2026-11')).toBe(true);
		expect(isOutstanding(task({ '2026-09': bucket('in_progress', true) }), null)).toBe(true);
	});

	it('flags an occurrence overdue since before the displayed period', () => {
		const earlier_overdue = { count: 2, node_id: 'oldest' };
		expect(isOutstanding({ bucket_status: {}, earlier_overdue }, '2026-11')).toBe(true);
		expect(
			isOutstanding({ bucket_status: {}, earlier_overdue: { count: 0, node_id: null } }, '2026-11')
		).toBe(false);
	});

	it('flags open work in the current period', () => {
		expect(isOutstanding(task({ '2026-11': bucket('pending', false) }), '2026-11')).toBe(true);
		expect(isOutstanding(task({ '2026-11': bucket('in_progress', false) }), '2026-11')).toBe(true);
	});

	it('ignores future, closed and empty periods', () => {
		expect(isOutstanding(task({ '2026-12': bucket('pending', false) }), '2026-11')).toBe(false);
		expect(isOutstanding(task({ '2026-11': bucket('completed', false) }), '2026-11')).toBe(false);
		expect(isOutstanding(task({ '2026-11': bucket('cancelled', false) }), '2026-11')).toBe(false);
		expect(isOutstanding(task({ '2026-11': bucket(null, false) }), '2026-11')).toBe(false);
		expect(isOutstanding({}, '2026-11')).toBe(false);
	});
});

describe('orderWindow', () => {
	it('keeps an ordered window as it is', () => {
		const window = { startYear: 2026, startMonth: 9, endYear: 2027, endMonth: 8 };
		expect(orderWindow(window)).toEqual(window);
		expect(orderWindow({ ...window, endYear: 2026, endMonth: 9 })).toEqual({
			...window,
			endYear: 2026,
			endMonth: 9
		});
	});

	it('collapses a window that starts after its end onto its start', () => {
		// ?start_year=2028 alone, on top of a default window ending in 2027.
		expect(orderWindow({ startYear: 2028, startMonth: 9, endYear: 2027, endMonth: 8 })).toEqual({
			startYear: 2028,
			startMonth: 9,
			endYear: 2028,
			endMonth: 9
		});
	});
});

// ── Grid: rows, sorting, grouping, view settings ─────────────────────────

const every = (frequency: string, interval: number) => ({ frequency, interval });

function row(task: Partial<ReviewTask> & { id: string }, folderName = 'Global'): TaskRow {
	return { task: { name: task.id, ...task }, folderId: folderName.toLowerCase(), folderName };
}

const ids = (rows: TaskRow[]) => rows.map((r) => r.task.id);

describe('flattenTasks', () => {
	it('lists every task with its domain', () => {
		const rows = flattenTasks([
			{ folder_id: 'f1', folder_name: 'Finance', tasks: [{ id: 'a', name: 'A' }] },
			{
				folder_id: 'f2',
				folder_name: 'IT',
				tasks: [
					{ id: 'b', name: 'B' },
					{ id: 'c', name: 'C' }
				]
			}
		]);
		expect(rows.map((r) => [r.task.id, r.folderId, r.folderName])).toEqual([
			['a', 'f1', 'Finance'],
			['b', 'f2', 'IT'],
			['c', 'f2', 'IT']
		]);
	});
});

describe('schedulePeriodDays', () => {
	it('orders cadences from daily to yearly', () => {
		const cadences = [
			every('YEARLY', 1),
			every('MONTHLY', 6),
			every('DAILY', 1),
			every('MONTHLY', 3),
			every('WEEKLY', 1),
			every('MONTHLY', 1)
		];
		const sorted = [...cadences].sort((a, b) => schedulePeriodDays(a)! - schedulePeriodDays(b)!);
		expect(sorted).toEqual([
			every('DAILY', 1),
			every('WEEKLY', 1),
			every('MONTHLY', 1),
			every('MONTHLY', 3),
			every('MONTHLY', 6),
			every('YEARLY', 1)
		]);
	});

	it('has no period without a known frequency', () => {
		expect(schedulePeriodDays(null)).toBeNull();
		expect(schedulePeriodDays({})).toBeNull();
		expect(schedulePeriodDays({ frequency: 'HOURLY', interval: 1 })).toBeNull();
	});

	it('treats a missing interval as 1', () => {
		expect(schedulePeriodDays({ frequency: 'WEEKLY' })).toBe(7);
	});
});

describe('sortRows', () => {
	const rows = [
		row({ id: 'yearly', name: 'Review policy', schedule: every('YEARLY', 1), ref_id: 'T-10' }),
		row({ id: 'weekly', name: 'Check backups', schedule: every('WEEKLY', 1), ref_id: 'T-2' }),
		row({ id: 'none', name: 'Ad hoc' }),
		row({ id: 'quarterly', name: 'Access review', schedule: every('MONTHLY', 3), ref_id: 'T-1' })
	];

	it('sorts by frequency, most frequent first, tasks without a cadence last', () => {
		expect(ids(sortRows(rows, { key: 'frequency', descending: false }))).toEqual([
			'weekly',
			'quarterly',
			'yearly',
			'none'
		]);
	});

	it('keeps rows without a value last when descending', () => {
		expect(ids(sortRows(rows, { key: 'frequency', descending: true }))).toEqual([
			'yearly',
			'quarterly',
			'weekly',
			'none'
		]);
	});

	it('sorts references naturally', () => {
		expect(ids(sortRows(rows, { key: 'ref', descending: false }))).toEqual([
			'quarterly',
			'weekly',
			'yearly',
			'none'
		]);
	});

	it('breaks ties on the task name', () => {
		const tied = [
			row({ id: '2', name: 'Beta', schedule: every('MONTHLY', 1) }),
			row({ id: '1', name: 'alpha', schedule: every('MONTHLY', 1) })
		];
		expect(ids(sortRows(tied, { key: 'frequency', descending: true }))).toEqual(['1', '2']);
	});

	it('sorts by domain and by next occurrence', () => {
		const mixed = [
			row({ id: 'b', next_occurrence: '2026-12-01' }, 'IT'),
			row({ id: 'a', next_occurrence: '2027-01-15' }, 'Finance'),
			row({ id: 'c', next_occurrence: null }, 'Audit')
		];
		expect(ids(sortRows(mixed, { key: 'domain', descending: false }))).toEqual(['c', 'a', 'b']);
		expect(ids(sortRows(mixed, { key: 'nextDue', descending: false }))).toEqual(['b', 'a', 'c']);
	});

	it('does not mutate its input', () => {
		const before = ids(rows);
		sortRows(rows, { key: 'name', descending: false });
		expect(ids(rows)).toEqual(before);
	});
});

describe('groupRows', () => {
	const labels = {
		unassigned: 'Unassigned',
		frequency: (schedule: { frequency?: string; interval?: number } | null | undefined) =>
			schedule ? `${schedule.frequency}/${schedule.interval}` : null
	};
	const alice = { id: 'u1', str: 'Alice' };
	const bob = { id: 'u2', str: 'Bob' };
	const rows = [
		row({ id: 'a', schedule: every('YEARLY', 1), assigned_to: [bob] }, 'IT'),
		row({ id: 'b', schedule: every('WEEKLY', 1), assigned_to: [alice, bob] }, 'Finance'),
		row({ id: 'c', schedule: every('YEARLY', 1), assigned_to: [] }, 'IT'),
		row({ id: 'd', assigned_to: [alice] }, 'Finance')
	];
	const shape = (groups: ReturnType<typeof groupRows>) =>
		groups.map((group) => [group.label, ids(group.rows)]);

	it('keeps a single unlabelled group without grouping', () => {
		expect(shape(groupRows(rows, 'none', labels))).toEqual([['', ['a', 'b', 'c', 'd']]]);
		expect(groupRows([], 'none', labels)).toEqual([]);
	});

	it('groups by domain in alphabetical order, keeping the row order', () => {
		expect(shape(groupRows(rows, 'domain', labels))).toEqual([
			['Finance', ['b', 'd']],
			['IT', ['a', 'c']]
		]);
	});

	it('groups by frequency from frequent to rare, tasks without a cadence last', () => {
		expect(shape(groupRows(rows, 'frequency', labels))).toEqual([
			['WEEKLY/1', ['b']],
			['YEARLY/1', ['a', 'c']],
			['—', ['d']]
		]);
	});

	it('lists a task under each of its assignees, unassigned last', () => {
		expect(shape(groupRows(rows, 'assignee', labels))).toEqual([
			['Alice', ['b', 'd']],
			['Bob', ['a', 'b']],
			['Unassigned', ['c']]
		]);
	});
});

describe('parseViewSettings', () => {
	it('falls back to the defaults', () => {
		expect(parseViewSettings(null)).toEqual(defaultViewSettings());
		expect(parseViewSettings('not json')).toEqual(defaultViewSettings());
		expect(parseViewSettings('42')).toEqual(defaultViewSettings());
	});

	it('restores stored settings', () => {
		const stored = {
			compact: true,
			grouping: 'assignee',
			sort: { key: 'name', descending: true },
			columns: ['domain', 'ref'],
			columnOrder: ['name', 'domain', 'ref', 'frequency', 'assignee', 'appliedControl', 'nextDue'],
			paneWidth: 480
		};
		expect(parseViewSettings(JSON.stringify(stored))).toEqual({
			...stored,
			// The shown columns are a set: their order is columnOrder's business.
			columns: ['ref', 'domain']
		});
	});

	it('groups by domain and keeps the domain column by default', () => {
		const settings = defaultViewSettings();
		expect(settings.grouping).toBe('domain');
		expect(settings.columns).toContain('domain');
	});

	it('completes a stored column order', () => {
		const order = (columnOrder: unknown) =>
			parseViewSettings(JSON.stringify({ columnOrder })).columnOrder;

		// Unknown and repeated names dropped, missing columns appended.
		expect(order(['domain', 'bogus', 'name', 'domain'])).toEqual([
			'domain',
			'name',
			'ref',
			'frequency',
			'assignee',
			'appliedControl',
			'nextDue'
		]);
		expect(order('name')).toEqual(defaultViewSettings().columnOrder);
	});

	it('ignores unusable fields one by one', () => {
		const settings = parseViewSettings(
			JSON.stringify({
				compact: 'yes',
				grouping: 'colour',
				sort: { key: 'size' },
				columns: ['assignee', 'bogus'],
				paneWidth: 99999
			})
		);
		expect(settings).toEqual({
			...defaultViewSettings(),
			columns: ['assignee'],
			paneWidth: clampPaneWidth(99999)
		});
	});

	it('accepts an empty column list', () => {
		expect(parseViewSettings(JSON.stringify({ columns: [] })).columns).toEqual([]);
	});
});

describe('moveColumn', () => {
	const order = defaultViewSettings().columnOrder;

	it('takes the place of the target, in either direction', () => {
		expect(moveColumn(order, 'ref', 'frequency').slice(0, 3)).toEqual(['name', 'frequency', 'ref']);
		expect(moveColumn(order, 'domain', 'ref').slice(0, 3)).toEqual(['domain', 'ref', 'name']);
	});

	it('leaves the order alone when there is nothing to move', () => {
		expect(moveColumn(order, 'name', 'name')).toBe(order);
		expect(moveColumn(['name', 'ref'], 'domain', 'ref')).toEqual(['name', 'ref']);
	});
});

describe('clampPaneWidth', () => {
	it('keeps the width within bounds', () => {
		expect(clampPaneWidth(10)).toBe(220);
		expect(clampPaneWidth(500.4)).toBe(500);
		expect(clampPaneWidth(5000)).toBe(1200);
	});
});
