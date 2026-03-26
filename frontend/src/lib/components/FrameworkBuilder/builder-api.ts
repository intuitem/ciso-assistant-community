/**
 * API functions for the framework builder draft workflow.
 * All calls go to /frameworks/{frameworkId}/builder which proxies to Django.
 *
 * Framework ID is passed explicitly to each function (not stored as module state)
 * to avoid issues with Vite HMR resetting module-level variables.
 */

export interface DraftJSON {
	framework_meta: {
		name: string;
		description: string | null;
		annotation?: string | null;
		locale?: string;
		translations?: Record<string, Record<string, string>>;
		available_languages?: string[];
		min_score: number;
		max_score: number;
		scores_definition: Record<string, unknown> | null;
		implementation_groups_definition: Record<string, unknown>[] | null;
		outcomes_definition: Record<string, unknown>[] | null;
		field_visibility?: Record<string, string>;
	};
	nodes: Record<string, unknown>[];
	questions: Record<string, unknown>[];
	choices: Record<string, unknown>[];
}

async function handleResponse(res: Response): Promise<unknown> {
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: 'Request failed' }));
		throw new Error(err.detail ?? err.error ?? JSON.stringify(err));
	}
	if (res.status === 204) return null;
	return res.json();
}

/** Start editing: POST to create/return the editing_draft */
export interface StartEditingResult {
	draft: DraftJSON;
	resumed: boolean; // true if resuming an existing draft, false if freshly created from live data
}

export async function apiStartEditing(frameworkId: string): Promise<StartEditingResult> {
	const res = await fetch(`/frameworks/${frameworkId}/builder`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'start-editing' })
	});
	const data = (await handleResponse(res)) as { editing_draft: DraftJSON; status: string };
	return {
		draft: data.editing_draft,
		resumed: data.status === 'already_editing'
	};
}

/** Save draft: PATCH to persist the current draft state */
export async function apiSaveDraft(frameworkId: string, draft: DraftJSON): Promise<void> {
	const res = await fetch(`/frameworks/${frameworkId}/builder`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'save-draft', editing_draft: draft })
	});
	await handleResponse(res);
}

/** Publish draft: POST to reconcile draft into relational DB */
export async function apiPublishDraft(frameworkId: string): Promise<void> {
	const res = await fetch(`/frameworks/${frameworkId}/builder`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'publish-draft' })
	});
	await handleResponse(res);
}

/** Discard draft: POST to throw away the draft */
export async function apiDiscardDraft(frameworkId: string): Promise<void> {
	const res = await fetch(`/frameworks/${frameworkId}/builder`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'discard-draft' })
	});
	await handleResponse(res);
}
