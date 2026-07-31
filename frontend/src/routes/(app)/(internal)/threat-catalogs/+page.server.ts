import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/threat-catalogs/`);
	const catalogs = await res.json();

	return { catalogs: catalogs.results ?? [] };
};
