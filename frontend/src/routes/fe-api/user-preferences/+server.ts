import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, request }) => {
	const endpoint = `${BASE_API_URL}/user-preferences/`;
	const req = await fetch(endpoint);
	const status = await req.status;
	const responseData = await req.json();

	return new Response(JSON.stringify(responseData), {
		status: status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

export const PATCH: RequestHandler = async ({ fetch, request }) => {
	const newPreferences = await request.text();
	const requestInitOptions: RequestInit = {
		method: 'PATCH',
		body: newPreferences
	};

	const endpoint = `${BASE_API_URL}/user-preferences/`;
	const req = await fetch(endpoint, requestInitOptions);
	const status = await req.status;
	const responseData = await req.text();

	return new Response(responseData, {
		status: status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
