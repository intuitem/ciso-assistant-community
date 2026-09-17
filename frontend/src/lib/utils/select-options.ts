import { formatSelectFieldData } from '$lib/utils/load';
import type { SelectField } from '$lib/utils/crud';

/**
 * Fetch a model's choice-field options on demand, client-side.
 *
 * Detail pages used to populate these during the server load, one request per
 * select field per related tab, on every page view — for create forms most
 * visits never open. `loadDetail` now leaves them empty and this fills them when
 * a form is actually opened.
 *
 * A no-op when options are already present, so the pages that still provide them
 * server-side are unaffected.
 */
const cache = new Map<string, Record<string, unknown>>();

export async function ensureSelectOptions(model: Record<string, any>): Promise<void> {
	if (!model) return;
	// Already provided (server load, or a previous open of this modal).
	if (model.selectOptions && Object.keys(model.selectOptions).length > 0) return;

	// Call sites pass either a ModelInfo or a detail page's related-model entry,
	// which carries the ModelInfo under `info`.
	const info = model.info ?? model;
	const selectFields: SelectField[] = info?.selectFields ?? [];
	if (!selectFields.length) return;

	const urlModel = info.urlModel ?? model.urlModel;
	if (!urlModel) return;

	const parents = selectFields
		.map((f) => (f.formNestedField ? model.initialData?.[f.formNestedField] : ''))
		.join(',');
	const key = `${urlModel}:${parents}`;

	const cached = cache.get(key);
	if (cached) {
		model.selectOptions = cached;
		return;
	}

	let complete = true;
	const entries = await Promise.all(
		selectFields.map(async (selectField) => {
			const query = new URLSearchParams({ field: selectField.field });
			const parent = selectField.formNestedField
				? model.initialData?.[selectField.formNestedField]
				: null;
			if (parent) query.set('detail', parent);
			const response = await fetch(`/${urlModel}/select-options?${query}`);
			if (!response.ok) {
				complete = false;
				console.error(`Failed to fetch options for ${selectField.field}: ${response.statusText}`);
				return [selectField.field, []];
			}
			return [selectField.field, formatSelectFieldData(await response.json(), selectField)];
		})
	);

	const options = Object.fromEntries(entries);
	if (complete) cache.set(key, options);
	model.selectOptions = options;
}
