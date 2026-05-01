import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/`);
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json();
	const res = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/mapping/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/`, {
		method: 'DELETE'
	});
	if (res.status === 204) {
		return new Response(null, { status: 204 });
	}
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
