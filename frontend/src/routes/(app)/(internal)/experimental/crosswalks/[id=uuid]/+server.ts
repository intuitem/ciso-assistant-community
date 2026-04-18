import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/crosswalks`;

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${ENDPOINT}/${params.id}/`);
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data);
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json();
	const res = await fetch(`${ENDPOINT}/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data);
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${ENDPOINT}/${params.id}/`, { method: 'DELETE' });
	if (res.status === 204) return new Response(null, { status: 204 });
	const data = await res.json().catch(() => ({}));
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data, { status: res.status });
};

export const POST: RequestHandler = async ({ fetch, params, url, request }) => {
	// Sub-action: /{id}?action=regenerate proxies to /{id}/regenerate/
	const action = url.searchParams.get('action');
	if (action === 'regenerate') {
		const body = await request.json().catch(() => ({}));
		const res = await fetch(`${ENDPOINT}/${params.id}/regenerate/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		const data = await res.json();
		if (!res.ok) error(res.status as NumericRange<400, 599>, data);
		return json(data);
	}
	error(400, { error: 'Unknown action' });
};
