import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/crosswalks/${params.id}/`);
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		error(res.status as any, body);
	}
	const crosswalk = await res.json();
	return { crosswalk };
}) satisfies PageServerLoad;
