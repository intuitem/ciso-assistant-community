import type { PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'risk-scenarios';
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	const scenario = await fetch(baseEndpoint).then((res) => res.json());

	const tables: Record<string, any> = {};

	for (const key of ['assets', 'threats', 'applied-controls'] as urlModel[]) {
		const keyEndpoint = `${BASE_API_URL}/${key}/?risk_scenarios=${params.id}`;
		const response = await fetch(keyEndpoint);
		if (response.ok) {
			const data = await response.json().then((data) => data.results);

			const metaData = tableSourceMapper(data, ['id', 'status']);

			const bodyData = tableSourceMapper(data, listViewFields[key].body);

			const table: TableSource = {
				head: listViewFields[key].head,
				body: bodyData,
				meta: metaData
			};
			tables[key] = table;
		} else {
			console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
		}
	}

	const riskMatrix = await fetch(`${BASE_API_URL}/risk-matrices/${object.risk_matrix}/`)
		.then((res) => res.json())
		.then((res) => JSON.parse(res.json_definition));

	return { scenario, tables, riskMatrix };
}) satisfies PageServerLoad;
