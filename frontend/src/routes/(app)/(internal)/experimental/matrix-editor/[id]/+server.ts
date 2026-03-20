import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/risk-matrix-drafts`;

export const PATCH: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.json();
	const res = await fetch(`${ENDPOINT}/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	const data = await res.json();
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, data);
	}
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${ENDPOINT}/${params.id}/`, {
		method: 'DELETE'
	});
	if (!res.ok && res.status !== 204) {
		const data = await res.json();
		error(res.status as NumericRange<400, 599>, data);
	}
	return new Response(null, { status: 204 });
};
