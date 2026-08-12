/**
 * API functions for the framework builder draft workflow.
 *
 * The target is passed explicitly to each function (not stored as module
 * state) to avoid issues with Vite HMR resetting module-level variables.
 * A framework UUID targets /frameworks/{id}/builder; a path (starting with
 * '/') is used verbatim, which lets other hosts speaking the same _action
 * protocol (e.g. the library builder editing a framework inside a
 * LibraryDraft document) reuse the whole editor.
 */

function apiUrl(target: string): string {
	return target.startsWith('/') ? target : `/frameworks/${target}/builder`;
}

export interface DraftJSON {
	schema_version?: number;
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
		urn_namespace?: string;
		ref_id?: string | null;
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

/** Save draft: PATCH to persist the current draft state */
export async function apiSaveDraft(frameworkId: string, draft: DraftJSON): Promise<void> {
	const res = await fetch(apiUrl(frameworkId), {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'save-draft', editing_draft: draft })
	});
	await handleResponse(res);
}

/** Reference catalog: pickable threats / reference controls for node links. */
export interface ReferentialCatalogItem {
	urn: string;
	ref_id: string | null;
	name: string | null;
	category?: string | null;
	csf_function?: string | null;
}

export interface ReferentialCatalogSource {
	library_urn: string;
	name: string;
	kind: 'draft' | 'dependency' | 'external';
	missing?: boolean;
	threats: ReferentialCatalogItem[];
	reference_controls: ReferentialCatalogItem[];
}

export interface ReferentialCatalog {
	sources: ReferentialCatalogSource[];
	libraries: { id: string; library_urn: string; name: string; provider: string | null }[];
}

export async function apiReferenceCatalog(frameworkId: string): Promise<ReferentialCatalog> {
	const res = await fetch(apiUrl(frameworkId), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'reference-catalog' })
	});
	return (await handleResponse(res)) as ReferentialCatalog;
}

/** One library's objects, browsed on demand (undeclared dependencies). */
export async function apiBrowseReferenceLibrary(
	frameworkId: string,
	library: string
): Promise<ReferentialCatalogSource> {
	const res = await fetch(apiUrl(frameworkId), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'reference-catalog', library })
	});
	const data = (await handleResponse(res)) as { source: ReferentialCatalogSource };
	return data.source;
}

/** Create a threat / reference control owned by the hosting library draft. */
export async function apiCreateReferential(
	frameworkId: string,
	field: 'threats' | 'reference_controls',
	object: Record<string, unknown>
): Promise<ReferentialCatalogItem> {
	const res = await fetch(apiUrl(frameworkId), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ _action: 'create-referential', field, object })
	});
	const data = (await handleResponse(res)) as { object: Record<string, unknown> };
	return data.object as unknown as ReferentialCatalogItem;
}
