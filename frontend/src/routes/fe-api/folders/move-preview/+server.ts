import { BASE_API_URL } from '#lib/utils/constants.js';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const { ids } = await request.json();

	const response = await fetch(`${BASE_API_URL}/folders/move-preview/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ ids })
	});

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return json(await response.json());
};
