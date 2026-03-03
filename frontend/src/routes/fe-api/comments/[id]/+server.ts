import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.text();
	const endpoint = `${BASE_API_URL}/comments/${params.id}/`;
	const res = await fetch(endpoint, {
		method: 'PATCH',
		body,
		headers: {
			'Content-Type': 'application/json'
		}
	});
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/comments/${params.id}/`;
	const res = await fetch(endpoint, {
		method: 'DELETE'
	});

	if (res.status === 204) {
		return new Response(null, { status: 204 });
	}

	const responseData = await res.text();
	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
