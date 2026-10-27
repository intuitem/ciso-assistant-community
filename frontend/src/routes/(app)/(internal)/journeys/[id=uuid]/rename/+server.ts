import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, fetch, request }) => {
	const body = await request.json();
	const response = await fetch(`${BASE_API_URL}/journeys/${params.id}/rename/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Failed to rename journey' }));
		return Response.json(error, { status: response.status });
	}

	return Response.json(await response.json());
};
