import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

const ENDPOINT = 'pmbok/projects';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = `${BASE_API_URL}/${ENDPOINT}/${params.id}/${url.search || ''}`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: res.headers
	});
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const endpoint = `${BASE_API_URL}/${ENDPOINT}/${params.id}/`;
	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: res.headers
	});
};
