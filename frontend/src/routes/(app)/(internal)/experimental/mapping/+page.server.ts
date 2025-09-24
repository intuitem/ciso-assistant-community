import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/requirement-mapping-sets/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data };
}) satisfies PageServerLoad;
