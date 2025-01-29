import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';

import { getModelInfo } from '$lib/utils/crud';
import type { ModelInfo, urlModel } from '$lib/utils/types';
import type { LayoutServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const model: ModelInfo = getModelInfo(params.model!);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${model.listViewUrlParams || ''}`;
	const res = await fetch(endpoint);
	const data = await res.json();

	const bodyData = tableSourceMapper(data.results, listViewFields[params.model as urlModel].body);

	const headData: Record<string, string> = listViewFields[params.model as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[params.model as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: bodyData,
		meta: data
	};

	return { table };
}) satisfies LayoutServerLoad;
