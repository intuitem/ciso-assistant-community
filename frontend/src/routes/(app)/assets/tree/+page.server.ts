import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/assets/class-tree/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}

	return { classTree: await res.json(), title: 'assetsTree' };
}) satisfies PageServerLoad;
