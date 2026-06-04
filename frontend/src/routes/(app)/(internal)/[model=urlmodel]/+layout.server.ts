import { getListViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';

export const load = async ({ fetch, params }) => {
	// Include optional fields so the column selector can offer them; ModelTable strips
	// feature-flag-disabled columns client-side, so no flag filtering is needed here.
	const fields = getListViewFields({ key: params.model, featureFlags: {}, includeOptional: true });
	const headData: Record<string, string> = fields.body.reduce((obj, key, index) => {
		obj[key] = fields.head[index];
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
