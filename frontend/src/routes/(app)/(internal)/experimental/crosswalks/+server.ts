import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/crosswalks`;

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${ENDPOINT}/`);
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data);
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();
	const res = await fetch(`${ENDPOINT}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data, { status: res.status });
};
