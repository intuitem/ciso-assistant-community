import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchAllPages } from '#lib/utils/pagination.js';

export const isOpenTask = (task: Record<string, any>) =>
	['pending', 'in_progress'].includes(task.status ?? task.next_occurrence_status);

export async function fetchTasks(
	fetch: typeof globalThis.fetch,
	query = ''
): Promise<Record<string, any>[]> {
	const res = await fetch(`${BASE_API_URL}/task-templates/?limit=1000${query}`);
	return res.ok ? (await res.json()).results : [];
}

/**
 * Actor ids to prefill as the assignees of a task a reviewer raises in `folder`: the
 * preferred representatives among the respondents of the vendor's workspace (enclave),
 * or all of its respondents when none is preferred. Empty outside an enclave, for a
 * vendor raising a task in their own workspace, and when the lookup fails.
 */
export async function fetchVendorAssignees(
	fetch: typeof globalThis.fetch,
	folder: { id: string; content_type?: string } | undefined,
	isThirdParty: boolean
): Promise<string[]> {
	if (!folder || folder.content_type !== 'EN' || isThirdParty) return [];
	const respondentsUrl = `${BASE_API_URL}/actors/?respondents_of=${folder.id}&respondents_only=true`;
	try {
		const preferred = await fetchAllPages<{ id: string }>(
			fetch,
			`${respondentsUrl}&preferred_only=true`
		);
		const actors = preferred.length
			? preferred
			: await fetchAllPages<{ id: string }>(fetch, respondentsUrl);
		return actors.map((actor) => actor.id);
	} catch {
		return [];
	}
}

export async function countOpenTasks(fetch: typeof globalThis.fetch): Promise<number> {
	const res = await fetch(
		`${BASE_API_URL}/task-templates/?limit=1&next_occurrence_status=pending&next_occurrence_status=in_progress`
	);
	return res.ok ? (await res.json()).count : 0;
}
