import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const { url_slug, fields } = await request.json();

	if (!url_slug || !fields) {
		return new Response(JSON.stringify({ detail: 'Missing url_slug or fields' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const res = await fetch(`${BASE_API_URL}/${url_slug}/`, {
		method: 'POST',
		body: JSON.stringify(fields),
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
