// Saved-filter-eligible URLModels → their backend app_label.model, fetched
// from the backend (core/saved_filters/registry.py) instead of hardcoded --
// a backend model rename or a newly-eligible model then needs no frontend
// change. Fetched once per page load and cached for the module's lifetime.
let eligibleModelsPromise: Promise<Record<string, string>> | null = null;

export function getSavedFilterEligibleModels(): Promise<Record<string, string>> {
	if (!eligibleModelsPromise) {
		eligibleModelsPromise = fetch('/fe-api/saved-filters/eligible-models/')
			.then((res) => (res.ok ? res.json() : {}))
			.catch(() => ({}));
	}
	return eligibleModelsPromise;
}

export interface SavedFilterEntry {
	id: string;
	name: string;
	model: string;
	properties: Record<string, { value: string }[]>;
	updated_at: string;
}

export interface SharedSavedFilter {
	id: string;
	name: string;
	// The read serializer (list/GET) sends {id}; the write serializer
	// (POST/PATCH response) sends a plain id string -- callers must handle both.
	folder: string | { id: string };
	model: string;
	properties: Record<string, { value: string }[]>;
	updated_at: string;
}

export function sharedSavedFilterFolderId(folder: SharedSavedFilter['folder']): string {
	return typeof folder === 'string' ? folder : folder.id;
}
