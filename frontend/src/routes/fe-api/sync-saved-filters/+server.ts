import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/saved-filters/sync/`;
	const res = await fetch(endpoint, { method: 'POST' });
	if (!res.ok) {
		console.error(await res.json());
		error(res.status, 'Error syncing saved filters');
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
