import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/object-classifications/${params.id}/`);
	if (!res.ok) error(res.status, 'Not found');
	const scheme = await res.json();
	return { scheme };
};
