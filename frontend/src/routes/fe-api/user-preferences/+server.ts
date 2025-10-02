import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/user-preferences/`;
	const req = await fetch(endpoint);
	const status = await req.status;
	const responseData = await req.text();

	return new Response(responseData, {
		status: status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

export const PATCH: RequestHandler = async ({ fetch, request, cookies }) => {
	const newPreferences: {
		lang?: string;
		decimal_notation?: string;
	} = await request.json();

	const { lang, decimal_notation } = newPreferences;

	const requestInitOptions: RequestInit = {
		method: 'PATCH',
		body: JSON.stringify({ lang, decimal_notation })
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
