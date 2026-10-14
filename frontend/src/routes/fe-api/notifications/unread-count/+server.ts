import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/notifications/unread_count/`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		console.error(await res.json());
		error(res.status, 'Error fetching unread notification count');
	}

	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
