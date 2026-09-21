import { formatSelectFieldData } from '$lib/utils/select-field';
import type { SelectField } from '$lib/utils/crud';

/** Choice-field options, fetched when a form opens rather than on page load. */
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

	// Detail pages put the parent id on the model, everyone else passes it in.
	const parentOf = (field: string) => initialData?.[field] ?? model.initialData?.[field];

	const fetched: Record<string, unknown> = {};
	await Promise.all(
		missing.map(async (selectField) => {
			const query = new URLSearchParams({ model: urlModel, field: selectField.field });
			const parent = selectField.formNestedField ? parentOf(selectField.formNestedField) : null;
			if (parent) query.set('detail', parent);
			const url = `/select-options?${query}`;
			try {
				const response = await fetch(url);
				if (!response.ok) throw new Error(response.statusText);
				fetched[selectField.field] = formatSelectFieldData(await response.json(), selectField);
			} catch (e) {
				console.error(`Failed to fetch options for ${selectField.field} from ${url}`, e);
			}
		})
	);

	// Always set: forms index it unguarded. Always fresh: they rewrite option
	// values in place, and the model can outlive the modal.
	model.selectOptions = structuredClone({ ...existing, ...fetched });
}
