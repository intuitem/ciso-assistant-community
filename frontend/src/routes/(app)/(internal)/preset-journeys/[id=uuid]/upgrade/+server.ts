import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, fetch }) => {
	const response = await fetch(`${BASE_API_URL}/preset-journeys/${params.id}/upgrade/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});

	const data = await response.json().catch(() => ({}));

	if (!response.ok) {
		return json(data, { status: response.status });
	}

	return json(data);
};
