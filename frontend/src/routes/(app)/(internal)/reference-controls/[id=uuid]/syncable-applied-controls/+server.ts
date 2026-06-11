import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async (event) => {
	const requestInitOptions: RequestInit = {
		method: 'GET'
	};

	const endpoint = `${BASE_API_URL}/reference-controls/${event.params.id}/syncable-applied-controls/`;
	const res = await event.fetch(endpoint, requestInitOptions);
	const responseData = await res.json();

	if (!res.ok) {
		console.error(responseData);
	}

	return new Response(JSON.stringify(responseData), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
