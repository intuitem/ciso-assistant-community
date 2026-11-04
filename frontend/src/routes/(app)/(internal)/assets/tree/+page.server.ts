import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/assets/class-tree/`);
	if (!res.ok) {
		error(res.status, await res.text());
	}

	return { classTree: await res.json(), title: 'assetsTree' };
}) satisfies PageServerLoad;
