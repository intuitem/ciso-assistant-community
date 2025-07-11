
import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/ebios-rm/operating-modes/${params.id}/build_graph/`;
	const res = await fetch(endpoint);
	const data = await res.json();

	return { data };
}) satisfies PageServerLoad;
