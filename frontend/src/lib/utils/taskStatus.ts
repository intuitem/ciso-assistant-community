/**
 * Colours for a task occurrence's status.
 *
 * Kept here rather than in each component: the analytics page and the occurrence
 * panel had their own copies and drifted, ending up with pending and in-progress
 * swapped between two views of the same data.
 */
import { localIsoDate } from './control-plan';

// Charts: hex rather than Tailwind classes, because ECharts needs a colour value.
export const TASK_STATUS_FALLBACK_COLOR = '#a3a3a3';

export const TASK_STATUS_COLORS: Record<string, string> = {
	// No occurrence has been generated yet — analytics only.
	_unset: '#cbd5e1',
	// Pending warns: nobody has picked it up yet. In progress is the calmer state.
	pending: '#f59e0b',
	in_progress: '#3b82f6',
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

const OPEN_STATUSES = ['pending', 'in_progress'];

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

/** Open and due before today, in the browser's time zone. Due today is not late yet. */
export function isOccurrenceLate(occurrence: { status: string; due_date: string | null }): boolean {
	const { status, due_date } = occurrence;
	if (!due_date || !OPEN_STATUSES.includes(status)) return false;
	const due = due_date.includes('T') ? localIsoDate(new Date(due_date)) : due_date;
	return due < localIsoDate(new Date());
}
