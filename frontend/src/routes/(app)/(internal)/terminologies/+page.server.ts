import { BASE_API_URL } from '#lib/utils/constants.js';
import { m } from '#paraglide/messages.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/terminologies/summary/`);
	if (!res.ok) error(res.status, 'Error loading terminologies');
	return { fields: await res.json(), title: m.terminologies() };
};
