import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ url, fetch }) => {
	const endpoint = new URL(`${BASE_API_URL}${url.pathname}`);
	url.searchParams.forEach((value, key) => {
		endpoint.searchParams.append(key, value);
	});

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching object count');
	}

	const count = await res.json();
	return new Response(JSON.stringify(count), {
		headers: {
			'Content-Type': 'aopplication/json'
		}
	});
};
