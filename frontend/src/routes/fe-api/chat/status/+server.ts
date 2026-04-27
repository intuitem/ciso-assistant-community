import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/chat/status/`);
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
