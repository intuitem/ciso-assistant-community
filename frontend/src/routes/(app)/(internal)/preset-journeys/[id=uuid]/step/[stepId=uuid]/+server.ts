import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();

	const response = await fetch(`${BASE_API_URL}/preset-journey-steps/${params.stepId}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Failed to update step' }));
		return json(error, { status: response.status });
	}

	const result = await response.json();
	return json(result);
};
