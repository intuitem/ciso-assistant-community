import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Create a level under this scheme.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json();
	const res = await fetch(`${BASE_API_URL}/classification-levels/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ ...body, object_classification: params.id })
	});
	return json(await res.json().catch(() => null), { status: res.status });
};

// Update a level (rank, visibility, name, color…). Body carries the level id.
export const PATCH: RequestHandler = async ({ fetch, request }) => {
	const { id, ...body } = await request.json();
	const res = await fetch(`${BASE_API_URL}/classification-levels/${id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	return json(await res.json().catch(() => null), { status: res.status });
};

export const DELETE: RequestHandler = async ({ fetch, url }) => {
	const id = url.searchParams.get('level');
	const res = await fetch(`${BASE_API_URL}/classification-levels/${id}/`, { method: 'DELETE' });
	if (!res.ok) return json(await res.json().catch(() => null), { status: res.status });
	return new Response(null, { status: 204 });
};
