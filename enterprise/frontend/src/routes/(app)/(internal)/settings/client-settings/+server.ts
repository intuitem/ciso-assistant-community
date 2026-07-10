import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	interface ClientInfo {
		name: string;
	}

	const endpoint = `${BASE_API_URL}/client-settings/info/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const errorBody = await res.text().catch(() => 'unknown error');
		console.error('Error fetching client info:', res.status, errorBody);
		error(400, 'Error fetching client info');
	}

	const client: ClientInfo = await res.json();

	return new Response(JSON.stringify(client), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
