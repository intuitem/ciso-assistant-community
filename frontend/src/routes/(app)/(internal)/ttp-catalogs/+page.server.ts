import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const catalogs = await fetchAllPages(fetch, `${BASE_API_URL}/ttp-catalogs/`).catch((e) => {
		error(e.status ?? 500, e.message);
	});

	return { catalogs };
};
