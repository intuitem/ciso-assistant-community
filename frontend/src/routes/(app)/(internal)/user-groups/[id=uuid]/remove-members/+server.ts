import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const endpoint = `${BASE_API_URL}/user-groups/${params.id}/remove-members/`;
	const body = await request.text();

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body
	});
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
