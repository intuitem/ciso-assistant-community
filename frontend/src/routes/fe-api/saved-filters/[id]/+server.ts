import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ fetch, request, params }) => {
	const res = await fetch(`${BASE_API_URL}/saved-filters/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/saved-filters/${params.id}/`, {
		method: 'DELETE'
	});
	return new Response(null, { status: res.status });
};
