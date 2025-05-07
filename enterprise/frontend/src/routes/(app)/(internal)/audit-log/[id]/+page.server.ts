import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/log-entries/${params.id}/`;

	const res = await fetch(endpoint);
	const log = await res.json();

	return { log };
}) satisfies PageServerLoad;
