import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/threat-catalogs/`);
	if (!res.ok) {
		error(res.status, await res.text());
	}
	const catalogs = await res.json();

	return { catalogs: catalogs.results ?? [] };
};
