import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/threat-catalogs/${params.id}/matrix/`);
	const matrix = await res.json();

	return { matrix };
};
