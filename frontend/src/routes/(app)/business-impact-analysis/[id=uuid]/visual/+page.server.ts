import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/resilience/business-impact-analysis/${params.id}/build-table/`;
	const res = await fetch(endpoint);
	const data = await res.json();

	return { data };
}) satisfies PageServerLoad;
