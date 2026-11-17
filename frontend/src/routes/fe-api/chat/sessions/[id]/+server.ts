import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${encodeURIComponent(params.id)}/`);
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${encodeURIComponent(params.id)}/`, {
		method: 'DELETE'
	});

	if (!res.ok) {
		const body = await res.text();
		return new Response(body, {
			status: res.status,
			headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' }
		});
	}
	return new Response(null, { status: 204 });
};
