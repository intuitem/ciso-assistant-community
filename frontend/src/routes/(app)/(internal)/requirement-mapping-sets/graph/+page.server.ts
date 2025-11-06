import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/requirement-mapping-sets/graph-data`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: m.inspect() };
};
