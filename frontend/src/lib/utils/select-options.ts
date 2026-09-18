import { formatSelectFieldData } from '$lib/utils/load';
import type { SelectField } from '$lib/utils/crud';

/** A model's choice-field options, fetched when a form opens rather than during
 * the server load. Only fields nobody has provided yet are fetched. */

// Per field, so a page that pre-filled some of them still gets the rest. Values
// are cloned in and out: consumers rewrite option values in place
// (AppliedControlPolicyForm), which would otherwise poison the entry.
const cache = new Map<string, unknown>();

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

	const existing = model.selectOptions ?? {};
	const missing = selectFields.filter((f) => !(f.field in existing));
	if (!missing.length) return;

	// Detail pages put the parent id on the model, everyone else passes it in.
	const parentOf = (field: string) => initialData?.[field] ?? model.initialData?.[field];

	const fetched: Record<string, unknown> = {};
	await Promise.all(
		missing.map(async (selectField) => {
			const parent = selectField.formNestedField ? parentOf(selectField.formNestedField) : null;
			// Parent-scoped options follow that parent's scale, which can be
			// edited, so they are never cached.
			const key = parent ? null : `${urlModel}:${selectField.field}`;
			const hit = key && cache.get(key);
			if (hit) {
				fetched[selectField.field] = structuredClone(hit);
				return;
			}
			const query = new URLSearchParams({ model: urlModel, field: selectField.field });
			if (parent) query.set('detail', parent);
			const url = `/select-options?${query}`;
			try {
				const response = await fetch(url);
				if (!response.ok) throw new Error(response.statusText);
				const options = formatSelectFieldData(await response.json(), selectField);
				if (key) cache.set(key, structuredClone(options));
				fetched[selectField.field] = options;
			} catch (e) {
				console.error(`Failed to fetch options for ${selectField.field} from ${url}`, e);
			}
		})
	);

	// Nothing to add and nothing there before: leave it unset so a form with its
	// own fallback (AppliedControlPolicyForm) can still use it.
	if (!Object.keys(fetched).length && !model.selectOptions) return;
	model.selectOptions = { ...existing, ...fetched };
}
