import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const { id } = params;

	const res = await fetch(`${BASE_API_URL}/requirement-mapping-sets/${id}/graph_data/`);
	const data = await res.json();

	// Streamed so the table payload never holds the graph back.
	// fetch resolves on 4xx/5xx, so reject explicitly.
	const tableData = fetch(`${BASE_API_URL}/requirement-mapping-sets/${id}/table_data/`).then(
		(response) => {
			if (!response.ok) {
				throw new Error(`table_data responded ${response.status}`);
			}
			return response.json();
		}
	);

	return { data, tableData };
};
