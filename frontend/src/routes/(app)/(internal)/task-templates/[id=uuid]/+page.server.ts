import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { Actions } from '@sveltejs/kit';
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
		limit: String(past ? PAST_WINDOW : UPCOMING_WINDOW)
	});
	const res = await fetch(`${BASE_API_URL}/task-nodes/?${params}`);
	if (!res.ok) return [];
	return (await res.json()).results ?? [];
}

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-templates');

	const data = await loadDetail({ event, model: modelInfo, id: event.params.id });

	const [pastOccurrences, upcomingOccurrences] = await Promise.all([
		fetchOccurrences(event.fetch, event.params.id, true),
		fetchOccurrences(event.fetch, event.params.id, false)
	]);

	return { ...data, pastOccurrences, upcomingOccurrences };
};

export const actions: Actions = {
	// Completing the next occurrence is the daily gesture, so it happens here rather
	// than a round trip to the occurrence page. Everything else links through.
	setOccurrenceStatus: async (event) => {
		const { id, status } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/task-nodes/${id}/`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ status })
		});
		return { success: res.ok, status: res.status };
	}
};
