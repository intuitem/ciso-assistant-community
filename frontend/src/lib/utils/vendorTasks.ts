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

/**
 * Actor ids to prefill as the assignees of a task a reviewer raises in `folder`: the
 * respondents of the vendor's workspace (enclave), the same actors the assignee picker
 * offers there. Empty outside an enclave, for a vendor raising a task in their own
 * workspace, and when the lookup fails.
 */
export async function fetchVendorAssignees(
	fetch: typeof globalThis.fetch,
	folder: { id: string; content_type?: string } | undefined,
	isThirdParty: boolean
): Promise<string[]> {
	if (!folder || folder.content_type !== 'EN' || isThirdParty) return [];
	const res = await fetch(
		`${BASE_API_URL}/actors/?respondents_of=${folder.id}&respondents_only=true&limit=200`
	);
	return res.ok ? (await res.json()).results.map((actor: { id: string }) => actor.id) : [];
}

export async function countOpenTasks(fetch: typeof globalThis.fetch): Promise<number> {
	const res = await fetch(
		`${BASE_API_URL}/task-templates/?limit=1&next_occurrence_status=pending&next_occurrence_status=in_progress`
	);
	return res.ok ? (await res.json()).count : 0;
}
