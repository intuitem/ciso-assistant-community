import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ fetch, request }) => {
	const preferences = await request.json();
	const requestInitOptions: RequestInit = {
		method: 'PATCH',
		body: JSON.stringify(preferences)
	};

	const endpoint = `${BASE_API_URL}/preferences/`;
	await fetch(endpoint, requestInitOptions);
	return new Response();
};
