import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/security-advisories/sync-euvd/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});

	const data = await res.json();
	return Response.json(data, { status: res.status });
};
