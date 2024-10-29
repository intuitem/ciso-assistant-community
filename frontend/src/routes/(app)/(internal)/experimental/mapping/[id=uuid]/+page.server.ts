import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const { id } = params;
	const endpoint = `${BASE_API_URL}/requirement-mapping-sets/${id}/graph_data`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data };
};
