import { BASE_API_URL } from '#lib/utils/constants.js';
import { formatDateOrDateTime } from '#lib/utils/datetime.js';
import { getLocale } from '#paraglide/runtime.js';

export interface OccurrenceSummary {
	id: string;
	due_date: string | null;
	status: string;
	expected_evidence?: { id: string; str: string }[];
	evidence_reviewed?: string[];
}

// A recurrent task's history is read at a glance rather than paged through, so it
// pulls a window of past occurrences in one go, and the upcoming ones the sync
// horizon holds: about a year of them, some fifty at most.
//
// Both windows hold more than a month of daily occurrences. A task has at most
// one occurrence per day, so the current month is always whole: only the month at
// the far end of a window can be cut (see wholeMonths).
const PAST_WINDOW = 120;
const UPCOMING_WINDOW = 60;

interface Occurrences {
	results: OccurrenceSummary[];
	count: number;
	/**
	 * The request did not go through. Kept apart from an empty result, so a
	 * page can say it could not check instead of reporting no occurrence.
	 */
	failed: boolean;
}

async function fetchOccurrences(
	fetch: typeof globalThis.fetch,
	params: Record<string, string>
): Promise<Occurrences> {
	try {
		const res = await fetch(`${BASE_API_URL}/task-nodes/?${new URLSearchParams(params)}`);
		if (!res.ok) return { results: [], count: 0, failed: true };
		const body = await res.json();
		const results = body.results ?? [];
		return { results, count: body.count ?? results.length, failed: false };
	} catch {
		return { results: [], count: 0, failed: true };
	}
}

/**
 * A window without the month at its far end when it filled up: the cut may fall
 * within that month, and the history draws a month from all its occurrences or
 * not at all.
 */
function wholeMonths({ results, count }: Occurrences): OccurrenceSummary[] {
	if (count <= results.length) return results;
	const monthOf = (occurrence: OccurrenceSummary) => occurrence.due_date?.slice(0, 7);
	const cut = monthOf(results[results.length - 1]);
	return results.filter((occurrence) => monthOf(occurrence) !== cut);
}

/** The occurrences of a task shown in its history: recent past ones and the next ones. */
export async function fetchOccurrenceHistory(
	fetch: typeof globalThis.fetch,
	taskTemplateId: string
) {
	const window = (past: boolean) =>
		fetchOccurrences(fetch, {
			task_template: taskTemplateId,
			past: String(past),
			// Explicit: without it the viewset's default created_at ordering wins over
			// the past filter's, and the window cuts by creation order. Past reads
			// newest-first so the window keeps the most recent history when it fills up.
			ordering: past ? '-due_date' : 'due_date',
			limit: String(past ? PAST_WINDOW : UPCOMING_WINDOW)
		});
	const [past, upcoming] = await Promise.all([window(true), window(false)]);
	return {
		pastOccurrences: wholeMonths(past),
		upcomingOccurrences: wholeMonths(upcoming),
		upcomingCount: upcoming.count,
		// Half a history would mislead as much as none.
		occurrencesFailed: past.failed || upcoming.failed
	};
}

/**
 * The occurrence of the same task due just before or just after a date, if any.
 * A task has at most one occurrence per due date (unique constraint), so the
 * strict comparison skips none.
 */
export async function fetchNeighbour(
	fetch: typeof globalThis.fetch,
	taskTemplateId: string,
	dueDate: string,
	before: boolean
): Promise<{ occurrence: OccurrenceSummary | null; failed: boolean }> {
	const { results, failed } = await fetchOccurrences(fetch, {
		task_template: taskTemplateId,
		[before ? 'due_date__lt' : 'due_date__gt']: dueDate,
		ordering: before ? '-due_date' : 'due_date',
		limit: '1'
	});
	return { occurrence: results[0] ?? null, failed };
}

/** An occurrence date in the user's locale, or '--'. */
export function formatOccurrenceDate(value: string | null): string {
	return formatDateOrDateTime(value, getLocale()) ?? '--';
}

/** Days from today to `value`, negative when past; null without a date. */
export function daysUntil(value: string | null): number | null {
	if (!value) return null;
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	// A date-only string is parsed as UTC midnight, which is the previous day in
	// time zones west of UTC; anchoring with a local time keeps the calendar date.
	const due = new Date(value.includes('T') ? value : `${value}T00:00:00`);
	due.setHours(0, 0, 0, 0);
	return Math.round((due.getTime() - today.getTime()) / 86400000);
}
