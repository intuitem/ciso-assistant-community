import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';

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

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return {
		table,
		modelVerboseName: urlParamModelVerboseName(params.model),
		modelDescriptionKey: urlParamModelDescriptionKey(params.model)
	};
};
