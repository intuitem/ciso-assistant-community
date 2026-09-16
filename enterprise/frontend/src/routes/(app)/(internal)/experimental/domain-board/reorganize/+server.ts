import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

/** Proxy for the reorganisation endpoint, colocated because only the board calls it. */
export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.text();
	const res = await fetch(`${BASE_API_URL}/folders/reorganize/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body
	});
	// 409 carries meaning, so pass the status through rather than collapsing it.
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
