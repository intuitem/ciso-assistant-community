import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/log-entries/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: 'm.auditLog()' };
}) satisfies PageServerLoad;
