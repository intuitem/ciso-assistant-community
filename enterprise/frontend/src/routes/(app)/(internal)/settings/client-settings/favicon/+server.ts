import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/client-settings/favicon/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching favicon');
	}
	const favicon = await res.json();

	return new Response(JSON.stringify(favicon), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
