/**
 * Colours for a task occurrence's status.
 *
 * Kept here rather than in each component: the analytics page and the occurrence
 * panel had their own copies and drifted, ending up with pending and in-progress
 * swapped between two views of the same data.
 */
import { localIsoDate, OPEN_STATUSES } from './control-plan';

// Charts: hex rather than Tailwind classes, because ECharts needs a colour value.
export const TASK_STATUS_FALLBACK_COLOR = '#a3a3a3';

export const TASK_STATUS_COLORS: Record<string, string> = {
	// No occurrence has been generated yet — analytics only.
	_unset: '#cbd5e1',
	// Same hues as OCCURRENCE_STYLES: red is kept for what is late.
	pending: '#0ea5e9',
	in_progress: '#8b5cf6',
	completed: '#22c55e',
	cancelled: '#94a3b8'
};

/**
 * How an occurrence is drawn on a timeline: the cells of the control plan and
 * the squares of the occurrence history, which must read the same way.
 *
 * Pastel fills glare on a dark background: dark mode uses deep, translucent ones.
 */
export const OCCURRENCE_STYLES = {
	none: 'border border-dashed border-surface-300-700',
	completed: 'bg-green-200 border border-green-600 dark:bg-green-800/70 dark:border-green-400',
	in_progress:
		'bg-violet-200 border border-violet-500 dark:bg-violet-800/70 dark:border-violet-400',
	planned: 'bg-sky-100 border border-sky-500 dark:bg-sky-800/60 dark:border-sky-400',
	overdue: 'bg-red-200 border border-red-500 dark:bg-red-800/70 dark:border-red-400',
	cancelled: 'bg-surface-200-800 border border-surface-500'
};
export type OccurrenceState = keyof typeof OCCURRENCE_STYLES;

/**
 * Red is reserved for what is late: open work whose due date has passed.
 * Open work that is not late yet is merely planned.
 */
export function occurrenceState(status: string | null | undefined, late: boolean): OccurrenceState {
	if (!status) return 'none';
	if (late) return 'overdue';
	if (status === 'pending') return 'planned';
	if (status in OCCURRENCE_STYLES) return status as OccurrenceState;
	return 'none';
}

/**
 * The status of a period holding several occurrences, null when it holds none.
 * Same rule as the control plan's (TaskTemplateViewSet._aggregate_status), so a
 * month reads alike in both: cancelled occurrences count only when all are, all
 * completed is completed, any progress is in progress.
 */
export function aggregateStatus(statuses: string[]): string | null {
	if (!statuses.length) return null;
	const active = statuses.filter((status) => status !== 'cancelled');
	if (!active.length) return 'cancelled';
	if (active.every((status) => status === 'completed')) return 'completed';
	if (active.some((status) => status === 'in_progress' || status === 'completed'))
		return 'in_progress';
	return active.includes('pending') ? 'pending' : active[0];
}

/** Open and due before today, in the browser's time zone. Due today is not late yet. */
export function isOccurrenceLate(occurrence: { status: string; due_date: string | null }): boolean {
	const { status, due_date } = occurrence;
	if (!due_date || !OPEN_STATUSES.includes(status)) return false;
	const due = due_date.includes('T') ? localIsoDate(new Date(due_date)) : due_date;
	return due < localIsoDate(new Date());
}

// What calls for attention first, then what is done, under way, to come, dropped.
const STATE_ORDER: OccurrenceState[] = [
	'overdue',
	'completed',
	'in_progress',
	'planned',
	'cancelled',
	'none'
];

/**
 * What a period holding several occurrences is made of: how many are drawn in
 * each state, without the states it has none of.
 */
export function countOccurrenceStates(
	occurrences: { status: string; due_date: string | null }[]
): [OccurrenceState, number][] {
	const counts = new Map<OccurrenceState, number>();
	for (const occurrence of occurrences) {
		const state = occurrenceState(occurrence.status, isOccurrenceLate(occurrence));
		counts.set(state, (counts.get(state) ?? 0) + 1);
	}
	return STATE_ORDER.filter((state) => counts.has(state)).map((state) => [
		state,
		counts.get(state)!
	]);
}
