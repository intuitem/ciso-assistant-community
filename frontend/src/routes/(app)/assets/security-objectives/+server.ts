import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/assets/security_objectives/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching security objectives');
	}

	const objectives: string[] = await res.json().then((obj) => obj.results);

	return new Response(JSON.stringify(objectives), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
