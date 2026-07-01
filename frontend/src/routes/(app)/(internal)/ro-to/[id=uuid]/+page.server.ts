import type { PageServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';
import { headData } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'ro-to';
	const model = getModelInfo(URLModel);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;
	const response = await event.fetch(endpoint);
	const data = await response.json();

	const table: TableSource = {
		head: headData('feared-events'),
		body: [],
		meta: []
	};

	return { data, table, title: `${safeTranslate(data.risk_origin)} / ${data.target_objective}` };
};
