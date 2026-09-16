import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const { id } = params;

	const res = await fetch(`${BASE_API_URL}/requirement-mapping-sets/${id}/graph_data/`);
	const data = await res.json();

	// Streamed: the table is the secondary view, so its payload must not hold the
	// graph back.
	const tableData = fetch(`${BASE_API_URL}/requirement-mapping-sets/${id}/table_data/`).then(
		(response) => response.json()
	);

	return { data, tableData };
};
