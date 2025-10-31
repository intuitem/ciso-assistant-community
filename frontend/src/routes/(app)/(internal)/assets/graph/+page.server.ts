import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, url }) => {
	const hideDomains = url.searchParams.get('hideDomains') === 'true';
	const endpoint = `${BASE_API_URL}/assets/graph/?hide_domains=${hideDomains}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, hideDomains };
}) satisfies PageServerLoad;
