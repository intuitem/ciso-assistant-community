import { listViewFields } from '$lib/utils/table';
import { IS_ENTERPRISE } from '$lib/utils/is_enterprise.js';
import { error } from '@sveltejs/kit';

import type { urlModel } from '$lib/utils/types';

export const load = async ({ fetch, params }) => {
	if (!IS_ENTERPRISE && params.model === 'qualifications') {
		throw error(404, 'Not found');
	}

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
