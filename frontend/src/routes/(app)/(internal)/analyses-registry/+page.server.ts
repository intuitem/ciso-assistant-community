import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';

import type { urlModel } from '$lib/utils/types';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const URLModel: urlModel = 'risk-assessments' as const;
	const endpoint = `${BASE_API_URL}/${URLModel}/`;

	const res = await fetch(endpoint);
	const data = await res.json().then((res) => res.results);

	const metaData = tableSourceMapper(data, ['id']);

	const bodyData = tableSourceMapper(data, listViewFields[URLModel].body);

	const table: TableSource = {
		head: listViewFields[URLModel].head,
		body: bodyData,
		meta: metaData
	};

	return { table, URLModel };
}) satisfies PageServerLoad;
