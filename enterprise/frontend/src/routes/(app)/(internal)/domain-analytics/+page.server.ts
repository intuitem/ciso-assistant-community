import { BASE_API_URL } from '#lib/utils/constants.js';
import { m } from '#paraglide/messages.js';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/folders/org_tree/?include_perimeters=false`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: m.domainAnalytics() };
}) satisfies PageServerLoad;
