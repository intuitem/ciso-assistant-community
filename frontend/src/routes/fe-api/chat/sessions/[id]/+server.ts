import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${params.id}/`);
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${params.id}/`, {
		method: 'DELETE'
	});

	return new Response(null, { status: res.status });
};
