import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	let body;
	try {
		body = await request.json();
	} catch {
		return json({ error: 'Invalid request body' }, { status: 400 });
	}

	const response = await fetch(`${BASE_API_URL}/settings/general/force_language/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	let data;
	try {
		data = await response.json();
	} catch {
		return json({ error: 'Unexpected response from server' }, { status: response.status || 500 });
	}

	return json(data, { status: response.status });
};
