import { BASE_API_URL } from '#lib/utils/constants.js';

export const isOpenTask = (task: Record<string, any>) =>
	['pending', 'in_progress'].includes(task.status ?? task.next_occurrence_status);

export async function fetchTasks(
	fetch: typeof globalThis.fetch,
	query = ''
): Promise<Record<string, any>[]> {
	const res = await fetch(`${BASE_API_URL}/task-templates/?limit=1000${query}`);
	return res.ok ? (await res.json()).results : [];
}
