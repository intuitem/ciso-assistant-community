import { BASE_API_URL } from '$lib/utils/constants';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();

	const response = await fetch(`${BASE_API_URL}/settings/general/force_language/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		const data = await response.json();
		return json(data, { status: response.status });
	}

	const data = await response.json();
	return json(data);
};
