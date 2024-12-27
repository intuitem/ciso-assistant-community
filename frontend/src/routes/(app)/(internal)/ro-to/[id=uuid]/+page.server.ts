import type { PageServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'ro-to';
	const model = getModelInfo(URLModel);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;
	const response = await event.fetch(endpoint);
	const data = await response.json();

	const relEndpoint = `${BASE_API_URL}/ebios-rm/feared-events?ro_to_couples=${event.params.id}`;
	const res = await event.fetch(relEndpoint);
	const revData = await res.json().then((res) => res.results);

	const tableFieldsRef = listViewFields['feared-events'];
	const tableFields = {
		head: [...tableFieldsRef.head],
		body: [...tableFieldsRef.body]
	};
	const index = tableFields.body.indexOf('ro_to_couples');
	if (index > -1) {
		tableFields.head.splice(index, 1);
		tableFields.body.splice(index, 1);
	}
	const bodyData = tableSourceMapper(revData, tableFields.body);

	const table: TableSource = {
		head: tableFields.head,
		body: bodyData,
		meta: revData
	};

	return { data, table, title: `${safeTranslate(data.risk_origin)} / ${data.target_objective}` };
};
