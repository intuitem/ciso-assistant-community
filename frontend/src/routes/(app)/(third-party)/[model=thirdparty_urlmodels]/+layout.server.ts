import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';

import type { urlModel } from '$lib/utils/types';

export const load = async ({ fetch, params }) => {
	const headData: Record<string, string> = listViewFields[params.model as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[params.model as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return { table };
};
