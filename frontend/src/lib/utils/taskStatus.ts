/**
 * Colours for a task occurrence's status.
 *
 * Kept here rather than in each component: the analytics page and the occurrence
 * panel had their own copies and drifted, ending up with pending and in-progress
 * swapped between two views of the same data.
 *
 * Hex rather than Tailwind classes, because ECharts needs a colour value and a
 * solid swatch reads the same in either theme.
 */
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

export function taskStatusColor(status: string): string {
	return TASK_STATUS_COLORS[status] ?? TASK_STATUS_FALLBACK_COLOR;
}
