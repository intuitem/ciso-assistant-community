import { BASE_API_URL } from '#lib/utils/constants.js';

export interface OccurrenceSummary {
	id: string;
	due_date: string | null;
	status: string;
	expected_evidence?: { id: string; str: string }[];
	evidence_reviewed?: string[];
}

// A recurrent task's history is read at a glance rather than paged through, so the
// strip pulls a window of past occurrences in one go. Upcoming ones are bounded by
// the sync horizon anyway, so a small page covers them.
const PAST_WINDOW = 120;
const UPCOMING_WINDOW = 12;

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
		pastOccurrences: past.results,
		upcomingOccurrences: upcoming.results,
		upcomingCount: upcoming.count,
		// Half a history would mislead as much as none.
		occurrencesFailed: past.failed || upcoming.failed
	};
}

/** The occurrence of the same task due just before or just after a date, if any. */
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
