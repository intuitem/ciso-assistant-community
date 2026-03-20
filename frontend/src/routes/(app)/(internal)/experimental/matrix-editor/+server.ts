import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/risk-matrix-drafts`;

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${ENDPOINT}/${url.searchParams ? '?' + url.searchParams.toString() : ''}`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();
	const res = await fetch(`${ENDPOINT}/`, {
		method: 'POST',
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
