import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

// A recurrent task's history is read at a glance rather than paged through, so the
// strip pulls a window of past occurrences in one go. Upcoming ones are bounded by
// the sync horizon anyway, so a small page covers them.
const PAST_WINDOW = 120;
const UPCOMING_WINDOW = 12;

async function fetchOccurrences(fetch: typeof globalThis.fetch, id: string, past: boolean) {
	const params = new URLSearchParams({
		task_template: id,
		past: String(past),
		// Explicit: without it the viewset's default created_at ordering wins over
		// the past filter's, and the window cuts by creation order. Past reads
		// newest-first so the window keeps the most recent history when it fills up.
		ordering: past ? '-due_date' : 'due_date',
		limit: String(past ? PAST_WINDOW : UPCOMING_WINDOW)
	});
	const res = await fetch(`${BASE_API_URL}/task-nodes/?${params}`);
	if (!res.ok) return { results: [], count: 0 };
	const body = await res.json();
	const results = body.results ?? [];
	return { results, count: body.count ?? results.length };
}

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-templates');

	const data = await loadDetail({ event, model: modelInfo, id: event.params.id });

	const [past, upcoming] = await Promise.all([
		fetchOccurrences(event.fetch, event.params.id, true),
		fetchOccurrences(event.fetch, event.params.id, false)
	]);

	return {
		...data,
		pastOccurrences: past.results,
		upcomingOccurrences: upcoming.results,
		upcomingCount: upcoming.count
	};
};
