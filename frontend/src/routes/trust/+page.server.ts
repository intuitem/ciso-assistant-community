import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/public/portals/primary/`);
	return { portal: res.ok ? await res.json() : null };
};
