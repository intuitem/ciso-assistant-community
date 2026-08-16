import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';

import type { urlModel } from '$lib/utils/types';

export const load = async ({ params }) => {
	const fields = listViewFields[params.model as urlModel];
	const head = [...fields.head, ...(fields.optionalFields?.head ?? [])];
	const body = [...fields.body, ...(fields.optionalFields?.body ?? [])];
	const headData: Record<string, string> = body.reduce((obj, key, index) => {
		obj[key] = head[index];
		return obj;
	}, {});

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return { table };
};
