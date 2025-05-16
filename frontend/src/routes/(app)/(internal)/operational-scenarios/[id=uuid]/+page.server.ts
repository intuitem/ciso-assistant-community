import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { getModelInfo } from '$lib/utils/crud';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'operational-scenarios';
	const model = getModelInfo(URLModel);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;
	const response = await event.fetch(endpoint);
	const data = await response.json();

	const tableFieldsRef = listViewFields['attack-paths'];
	const tableFields = {
		head: [...tableFieldsRef.head],
		body: [...tableFieldsRef.body]
	};
	const index = tableFields.body.indexOf('operational_scenarios');
	if (index > -1) {
		tableFields.head.splice(index, 1);
		tableFields.body.splice(index, 1);
	}

	const table: TableSource = {
		head: tableFields.head,
		body: [],
		meta: []
	};

	return { data, table, title: data.name };
};
