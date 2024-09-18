import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/license/`;

	const res = await fetch(endpoint);
	const license = await res.json();

	return { license };
}) satisfies PageServerLoad;
