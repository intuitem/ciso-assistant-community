import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/public/snapshots/${params.token}/`);
	if (!res.ok) error(404, 'Not found');
	return { snapshot: await res.json(), token: params.token };
};
