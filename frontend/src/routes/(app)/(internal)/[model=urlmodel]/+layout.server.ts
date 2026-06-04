import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';

export const load = async ({ fetch, params }) => {
	// Build the full column superset (defaults + optional fields), WITHOUT feature-flag
	// filtering: ModelTable strips flag-disabled columns client-side against the real flags,
	// and it can only filter the head down — never add a column back. Filtering here (no flags
	// available) would unconditionally drop every flagged column (e.g. inherent risk levels).
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
