import { formatSelectFieldData } from '$lib/utils/load';
import type { SelectField } from '$lib/utils/crud';

/** A model's choice-field options, fetched when a form opens rather than during
 * the server load. A no-op when something already provided them. */
const cache = new Map<string, Record<string, unknown>>();
const incomplete = new Set<string>();

export async function ensureSelectOptions(
	model: Record<string, any>,
	initialData: Record<string, any> = {}
): Promise<void> {
	if (!model) return;

	// A ModelInfo, or a detail page's related entry carrying one under `info`.
	const info = model.info ?? model;
	const selectFields: SelectField[] = info?.selectFields ?? [];
	if (!selectFields.length) return;

	const urlModel = info.urlModel ?? model.urlModel;
	if (!urlModel) return;

	// Detail pages put the parent id on the model, everyone else passes it in.
	const parentOf = (field: string) => initialData?.[field] ?? model.initialData?.[field];
	const parents = selectFields
		.map((f) => (f.formNestedField ? parentOf(f.formNestedField) : ''))
		.join(',');
	const key = `${urlModel}:${parents}`;

	// Already provided, unless a previous attempt only half-filled it.
	if (!incomplete.has(key) && model.selectOptions && Object.keys(model.selectOptions).length > 0)
		return;

	const cached = cache.get(key);
	if (cached) {
		// AppliedControlPolicyForm rewrites option values in place.
		model.selectOptions = structuredClone(cached);
		return;
	}

	let complete = true;
	const entries = await Promise.all(
		selectFields.map(async (selectField) => {
			const query = new URLSearchParams({ field: selectField.field });
			const parent = selectField.formNestedField ? parentOf(selectField.formNestedField) : null;
			if (parent) query.set('detail', parent);
			const url = `/${urlModel}/select-options?${query}`;
			try {
				const response = await fetch(url);
				if (!response.ok) throw new Error(response.statusText);
				return [selectField.field, formatSelectFieldData(await response.json(), selectField)];
			} catch (e) {
				complete = false;
				console.error(`Failed to fetch options for ${selectField.field} from ${url}`, e);
				return [selectField.field, []];
			}
		})
	);

	const options = Object.fromEntries(entries);
	if (complete) {
		cache.set(key, options);
		incomplete.delete(key);
	} else {
		incomplete.add(key);
	}
	model.selectOptions = options;
}
