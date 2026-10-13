import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.text();
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${params.id}/import/`, {
		method: 'POST',
		body,
		headers: {
			'Content-Type': 'application/json'
		}
	});

	const responseBody = await res.text();
	return new Response(responseBody, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
