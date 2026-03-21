import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/chat/sessions/`);
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.text();
	const res = await fetch(`${BASE_API_URL}/chat/sessions/`, {
		method: 'POST',
		body,
		headers: {
			'Content-Type': 'application/json'
		}
	});
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
