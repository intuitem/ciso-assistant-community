import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const DELETE: RequestHandler = async ({ params, fetch }) => {
	const response = await fetch(`${BASE_API_URL}/preset-journeys/${params.id}/`, {
		method: 'DELETE'
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Failed to delete journey' }));
		return json(error, { status: response.status });
	}

	return new Response(null, { status: 204 });
};
