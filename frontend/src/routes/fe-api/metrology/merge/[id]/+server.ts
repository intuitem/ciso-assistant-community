import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// Merge definition `id` into the one named in the body ({ into }).
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/${params.id}/merge/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
