import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/requirement-mapping-sets/`;

	const data = await fetchAllPages(fetch, endpoint);

	return { data, title: 'Visualize applied mapping data as a graph' };
}) satisfies PageServerLoad;
