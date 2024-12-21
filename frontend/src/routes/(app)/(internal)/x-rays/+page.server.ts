import { BASE_API_URL } from '$lib/utils/constants';
import * as m from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/projects/quality_check/`;

	const res = await fetch(endpoint);
	const data = await res.json().then((res) => res.results);

	return { data, title: m.xRays() };
}) satisfies PageServerLoad;
