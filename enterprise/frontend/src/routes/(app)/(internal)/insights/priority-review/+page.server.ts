import { BASE_API_URL } from '#lib/utils/constants.js';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, url }) => {
	// Only the matrix's own filter goes through: the table below writes its
	// cell filters (impact, effort) to the page URL too.
	const params = new URLSearchParams();
	for (const status of url.searchParams.getAll('exclude_status')) {
		params.append('exclude_status', status);
	}
	const query = params.size ? `?${params}` : '';
	const endpoint = `${BASE_API_URL}/applied-controls/impact_effort/${query}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data };
}) satisfies PageServerLoad;
