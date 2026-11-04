import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// A computed metric as the compose modal edits it (GET), and the edit (PUT).
const endpoint = (id: string) => `${BASE_API_URL}/metrology/metric-instances/${id}/composition/`;

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(endpoint(params.id));
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const PUT: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(endpoint(params.id), {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
