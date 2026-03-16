import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

async function proxyRequest(
	fetch: typeof globalThis.fetch,
	method: string,
	endpoint: string,
	id?: string,
	payload?: unknown
) {
	const url = id ? `${BASE_API_URL}/${endpoint}/${id}/` : `${BASE_API_URL}/${endpoint}/`;

	const res = await fetch(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		...(payload !== undefined ? { body: JSON.stringify(payload) } : {})
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	if (res.status === 204) {
		return new Response(null, { status: 204 });
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
}

export const POST: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, payload } = await request.json();
	return proxyRequest(fetch, 'POST', endpoint, undefined, payload);
};

export const PATCH: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, id, payload } = await request.json();
	return proxyRequest(fetch, 'PATCH', endpoint, id, payload);
};

export const DELETE: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, id } = await request.json();
	return proxyRequest(fetch, 'DELETE', endpoint, id);
};
