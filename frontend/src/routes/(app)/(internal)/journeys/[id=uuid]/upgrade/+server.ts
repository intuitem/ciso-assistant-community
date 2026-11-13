import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, fetch }) => {
	const response = await fetch(`${BASE_API_URL}/journeys/${params.id}/upgrade/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});

	const data = await response.json().catch(() => ({}));

	if (!response.ok) {
		return Response.json(data, { status: response.status });
	}

	return Response.json(data);
};
