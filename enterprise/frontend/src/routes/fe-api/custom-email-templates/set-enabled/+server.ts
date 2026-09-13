import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.text();
	const endpoint = `${BASE_API_URL}/custom-email-templates/set-enabled/`;
	const res = await fetch(endpoint, {
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
