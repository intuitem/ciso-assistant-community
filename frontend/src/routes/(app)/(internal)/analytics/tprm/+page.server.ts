import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entity-assessments/metrics/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: m.tprmOverview() };
}) satisfies PageServerLoad;
