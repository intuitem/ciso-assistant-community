import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';
import { CUSTOM_FIELD_HOST_MODELS, type CustomFieldDef } from '$lib/utils/customFields';
import { BASE_API_URL } from '$lib/utils/constants';

export const load = async ({ fetch, params }) => {
	// Full column superset (defaults + optional), unfiltered: ModelTable strips flag-disabled
	// columns client-side and can only narrow the head, never re-add a column.
	const base = listViewFields[params.model];
	const head = base ? [...base.head, ...(base.optionalFields?.head ?? [])] : [];
	const body = base ? [...base.body, ...(base.optionalFields?.body ?? [])] : [];
	const headData: Record<string, string> = body.reduce((obj, key, index) => {
		obj[key] = head[index];
		return obj;
	}, {});

	// `description` is a standard field on most objects — offer it as an opt-in column
	// (off by default) wherever a model doesn't already surface it.
	if (base && !body.includes('description')) {
		headData['description'] = 'description';
	}

	// Custom-field definitions drive both opt-in table columns and dynamic filters.
	let customFields: CustomFieldDef[] = [];
	const contentType = CUSTOM_FIELD_HOST_MODELS[params.model];
	if (contentType) {
		const res = await fetch(`${BASE_API_URL}/custom-fields/?model=${contentType}`);
		if (res.ok) {
			customFields = (await res.json()).results ?? [];
			// Visible fields become opt-in columns (offered in the picker, off by default).
			for (const def of customFields) {
				if (def.visible) headData[`cf__${def.key}`] = def.label_localized;
			}
		}
	}

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return {
		table,
		customFields,
		modelVerboseName: urlParamModelVerboseName(params.model),
		modelDescriptionKey: urlParamModelDescriptionKey(params.model)
	};
};
