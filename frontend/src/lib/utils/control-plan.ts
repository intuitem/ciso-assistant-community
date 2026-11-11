/**
 * Date helpers for the control plan (tasks review) page: which period the
 * page opens on, and where "now" sits on the time axis.
 *
 * Months are 1-based everywhere, matching the API's start_month / end_month.
 */

import type { TaskSchedule } from './taskSchedule';

export const GRANULARITIES = ['monthly', 'weekly', 'quarterly', 'semiannual'] as const;
export type Granularity = (typeof GRANULARITIES)[number];

export function isGranularity(value: string | null): value is Granularity {
	return GRANULARITIES.includes(value as Granularity);
}

export interface MonthWindow {
	startYear: number;
	startMonth: number;
	endYear: number;
	endMonth: number;
}

export interface Bucket {
	key: string;
	label: string;
	start: string;
	end: string;
}

/**
 * How many periods the rolling window shows before and after the current one.
 * Weeks are counted in weeks, then rounded out to whole months.
 */
const ROLLING_SPAN: Record<Granularity, { before: number; after: number }> = {
	monthly: { before: 2, after: 9 },
	weekly: { before: 2, after: 9 },
	quarterly: { before: 1, after: 3 },
	semiannual: { before: 1, after: 2 }
};

const MONTHS_PER_PERIOD: Record<Exclude<Granularity, 'weekly'>, number> = {
	monthly: 1,
	quarterly: 3,
	semiannual: 6
};

const DAY_MS = 24 * 60 * 60 * 1000;

function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
	const index = year * 12 + (month - 1) + delta;
	return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

/** The window the page opens on: a little past for context, mostly what is ahead. */
export function rollingWindow(today: Date, granularity: Granularity): MonthWindow {
	const { before, after } = ROLLING_SPAN[granularity];

	if (granularity === 'weekly') {
		const noon = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12);
		const first = new Date(noon.getTime() - before * 7 * DAY_MS);
		const last = new Date(noon.getTime() + after * 7 * DAY_MS);
		return {
			startYear: first.getFullYear(),
			startMonth: first.getMonth() + 1,
			endYear: last.getFullYear(),
			endMonth: last.getMonth() + 1
		};
	}

	const span = MONTHS_PER_PERIOD[granularity];
	const year = today.getFullYear();
	const month = today.getMonth() + 1;
	const periodStart = month - ((month - 1) % span);
	const start = shiftMonth(year, periodStart, -before * span);
	const end = shiftMonth(year, periodStart, after * span + span - 1);
	return {
		startYear: start.year,
		startMonth: start.month,
		endYear: end.year,
		endMonth: end.month
	};
}

export function yearWindow(year: number): MonthWindow {
	return { startYear: year, startMonth: 1, endYear: year, endMonth: 12 };
}

export function sameWindow(a: MonthWindow, b: MonthWindow): boolean {
	return (
		a.startYear === b.startYear &&
		a.startMonth === b.startMonth &&
		a.endYear === b.endYear &&
		a.endMonth === b.endMonth
	);
}

/** Local calendar date as YYYY-MM-DD, comparable with the API's bucket bounds. */
export function localIsoDate(date: Date): string {
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${date.getFullYear()}-${month}-${day}`;
}

export function isCurrentBucket(bucket: Pick<Bucket, 'start' | 'end'>, today: string): boolean {
	return bucket.start <= today && today <= bucket.end;
}

export interface MonthBand {
	key: string;
	year: number;
	month: number;
	span: number;
}

/**
 * Group consecutive buckets by the month they start in, to draw a month row
 * above week columns.
 */
export function monthBands(buckets: Pick<Bucket, 'start'>[]): MonthBand[] {
	const bands: MonthBand[] = [];
	for (const bucket of buckets) {
		const key = bucket.start.slice(0, 7);
		const last = bands[bands.length - 1];
		if (last && last.key === key) {
			last.span += 1;
		} else {
			const [year, month] = key.split('-').map(Number);
			bands.push({ key, year, month, span: 1 });
		}
	}
	return bands;
}

export interface BucketStatus {
	status: string | null;
	node_ids: string[];
	overdue?: boolean;
}

const OPEN_STATUSES = ['pending', 'in_progress'];

/**
 * A task is outstanding when it needs action now: an occurrence is overdue, or
 * the current period still has open work.
 */
export function isOutstanding(
	bucketStatus: Record<string, BucketStatus> | undefined,
	currentKey: string | null
): boolean {
	return Object.entries(bucketStatus ?? {}).some(
		([key, bucket]) =>
			bucket.overdue === true ||
			(key === currentKey && bucket.status !== null && OPEN_STATUSES.includes(bucket.status))
	);
}

// ── Grid: rows, sorting, grouping, view settings ─────────────────────────

export interface NamedRef {
	id?: string;
	str?: string;
	name?: string;
}

export interface ReviewTask {
	id: string;
	name: string;
	ref_id?: string | null;
	link?: string | null;
	schedule?: TaskSchedule | null;
	next_occurrence?: string | null;
	assigned_to?: NamedRef[];
	applied_controls?: NamedRef[];
	bucket_status?: Record<string, BucketStatus>;
}

export interface ReviewFolder {
	folder_id: string;
	folder_name: string;
	tasks: ReviewTask[];
}

/** One line of the grid: a task and the domain it lives in. */
export interface TaskRow {
	task: ReviewTask;
	folderId: string;
	folderName: string;
}

export function flattenTasks(folders: ReviewFolder[]): TaskRow[] {
	return folders.flatMap((folder) =>
		folder.tasks.map((task) => ({
			task,
			folderId: folder.folder_id,
			folderName: folder.folder_name
		}))
	);
}

export function refLabel(ref: NamedRef): string {
	return ref.str ?? ref.name ?? '';
}

export function joinLabels(refs: NamedRef[] | undefined): string {
	return (refs ?? []).map(refLabel).filter(Boolean).join(', ');
}

const FREQUENCY_DAYS: Record<string, number> = {
	DAILY: 1,
	WEEKLY: 7,
	MONTHLY: 30,
	YEARLY: 365
};

/**
 * Rough number of days between two occurrences, to order cadences from the
 * most to the least frequent: daily, weekly, monthly, quarterly (every 3
 * months), semester (every 6 months), yearly.
 */
export function schedulePeriodDays(schedule: TaskSchedule | null | undefined): number | null {
	const unit = FREQUENCY_DAYS[schedule?.frequency ?? ''];
	if (!unit) return null;
	const interval = Math.max(Math.trunc(Number(schedule?.interval ?? 1)) || 1, 1);
	return unit * interval;
}

export const SORT_KEYS = [
	'frequency',
	'name',
	'ref',
	'assignee',
	'appliedControl',
	'nextDue',
	'domain'
] as const;
export type SortKey = (typeof SORT_KEYS)[number];

export interface Sort {
	key: SortKey;
	descending: boolean;
}

type SortValue = string | number | null;

const SORT_VALUES: Record<SortKey, (row: TaskRow) => SortValue> = {
	frequency: (row) => schedulePeriodDays(row.task.schedule),
	name: (row) => row.task.name,
	ref: (row) => row.task.ref_id ?? null,
	assignee: (row) => joinLabels(row.task.assigned_to),
	appliedControl: (row) => joinLabels(row.task.applied_controls),
	nextDue: (row) => row.task.next_occurrence ?? null,
	domain: (row) => row.folderName
};

function compareText(a: string, b: string): number {
	return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

function compareValues(a: SortValue, b: SortValue): number {
	if (typeof a === 'number' && typeof b === 'number') return a - b;
	return compareText(String(a), String(b));
}

/**
 * Sort rows on one column. Rows without a value go last in both directions,
 * and ties fall back to the task name so the order is stable.
 */
export function sortRows(rows: TaskRow[], sort: Sort): TaskRow[] {
	const valueOf = SORT_VALUES[sort.key];
	const direction = sort.descending ? -1 : 1;
	return [...rows].sort((left, right) => {
		const a = valueOf(left);
		const b = valueOf(right);
		const aEmpty = a === null || a === '';
		const bEmpty = b === null || b === '';
		if (aEmpty !== bEmpty) return aEmpty ? 1 : -1;
		const primary = aEmpty ? 0 : compareValues(a, b) * direction;
		return (
			primary ||
			compareText(left.task.name, right.task.name) ||
			compareText(left.task.id, right.task.id)
		);
	});
}

export const GROUPINGS = ['none', 'domain', 'frequency', 'assignee'] as const;
export type Grouping = (typeof GROUPINGS)[number];

export interface RowGroup {
	key: string;
	label: string;
	rows: TaskRow[];
}

export interface GroupLabels {
	/** Group of the tasks nobody is assigned to. */
	unassigned: string;
	/** The cadence in words, e.g. "Every 3 months". */
	frequency: (schedule: TaskSchedule | null | undefined) => string | null;
}

const NO_VALUE_KEY = '';

/**
 * Split rows into groups, keeping the row order within each group.
 *
 * A task assigned to several actors is listed under each of them, so that a
 * group shows everything its assignee has to do.
 */
export function groupRows(rows: TaskRow[], grouping: Grouping, labels: GroupLabels): RowGroup[] {
	if (grouping === 'none') return rows.length ? [{ key: 'all', label: '', rows }] : [];

	const groups = new Map<string, RowGroup & { rank: number | null }>();
	const add = (key: string, label: string, rank: number | null, row: TaskRow) => {
		let group = groups.get(key);
		if (!group) {
			group = { key, label, rank, rows: [] };
			groups.set(key, group);
		}
		group.rows.push(row);
	};

	for (const row of rows) {
		if (grouping === 'domain') {
			add(row.folderId, row.folderName, null, row);
		} else if (grouping === 'frequency') {
			const days = schedulePeriodDays(row.task.schedule);
			if (days === null) add(NO_VALUE_KEY, '—', null, row);
			else {
				const { frequency, interval } = row.task.schedule ?? {};
				add(`${frequency}:${interval ?? 1}`, labels.frequency(row.task.schedule) ?? '—', days, row);
			}
		} else {
			const assignees = row.task.assigned_to ?? [];
			if (assignees.length === 0) add(NO_VALUE_KEY, labels.unassigned, null, row);
			for (const assignee of assignees) {
				add(assignee.id ?? refLabel(assignee), refLabel(assignee), null, row);
			}
		}
	}

	// The group without a value goes last; cadences go from frequent to rare.
	return [...groups.values()]
		.sort((a, b) => {
			if ((a.key === NO_VALUE_KEY) !== (b.key === NO_VALUE_KEY)) {
				return a.key === NO_VALUE_KEY ? 1 : -1;
			}
			if (a.rank !== null && b.rank !== null && a.rank !== b.rank) return a.rank - b.rank;
			return compareText(a.label, b.label);
		})
		.map(({ key, label, rows: groupRows }) => ({ key, label, rows: groupRows }));
}

/** Columns the user can show or hide next to the task name. */
export const OPTIONAL_COLUMNS = [
	'ref',
	'frequency',
	'assignee',
	'appliedControl',
	'nextDue',
	'domain'
] as const;
export type OptionalColumn = (typeof OPTIONAL_COLUMNS)[number];

export const PANE_WIDTH = { min: 220, max: 1200, initial: 560 } as const;

export function clampPaneWidth(width: number): number {
	return Math.min(PANE_WIDTH.max, Math.max(PANE_WIDTH.min, Math.round(width)));
}

/** How the grid is laid out; kept per browser, not in the URL. */
export interface ViewSettings {
	compact: boolean;
	grouping: Grouping;
	sort: Sort;
	columns: OptionalColumn[];
	paneWidth: number;
}

export function defaultViewSettings(): ViewSettings {
	return {
		compact: false,
		grouping: 'none',
		sort: { key: 'frequency', descending: false },
		columns: ['ref', 'frequency', 'assignee', 'appliedControl'],
		paneWidth: PANE_WIDTH.initial
	};
}

/**
 * Read stored view settings. These are display preferences written by an
 * earlier version of the page at worst, so anything unusable falls back to
 * its default, field by field, rather than breaking the page.
 */
export function parseViewSettings(raw: string | null): ViewSettings {
	const settings = defaultViewSettings();
	if (!raw) return settings;

	let stored: unknown;
	try {
		stored = JSON.parse(raw);
	} catch {
		return settings;
	}
	if (typeof stored !== 'object' || stored === null) return settings;
	const { compact, grouping, sort, columns, paneWidth } = stored as Record<string, unknown>;

	if (typeof compact === 'boolean') settings.compact = compact;
	if (GROUPINGS.includes(grouping as Grouping)) settings.grouping = grouping as Grouping;
	if (typeof sort === 'object' && sort !== null) {
		const { key, descending } = sort as Record<string, unknown>;
		if (SORT_KEYS.includes(key as SortKey)) {
			settings.sort = { key: key as SortKey, descending: descending === true };
		}
	}
	if (Array.isArray(columns)) {
		// Canonical order, unknown names dropped.
		settings.columns = OPTIONAL_COLUMNS.filter((column) => columns.includes(column));
	}
	if (typeof paneWidth === 'number' && Number.isFinite(paneWidth)) {
		settings.paneWidth = clampPaneWidth(paneWidth);
	}
	return settings;
}
