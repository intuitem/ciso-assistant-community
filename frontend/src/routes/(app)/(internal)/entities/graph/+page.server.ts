import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entities/graph/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error loading entities graph data');
	}

	const data = await res.json();

	return {
		data
	};
};
