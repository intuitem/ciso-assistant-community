import { BASE_API_URL } from '$lib/utils/constants';
import * as m from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/folders/org_tree/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: m.inspect() };
}) satisfies PageServerLoad;
