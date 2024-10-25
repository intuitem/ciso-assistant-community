import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/client-settings/logo/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching logo');
	}
	const logo = await res.json();

	return new Response(JSON.stringify(logo), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
