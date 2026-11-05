import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// A value typed on the metric's page: one sample, for a period when the
// metric has a frequency.
export const POST: RequestHandler = async ({ fetch, request }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/custom-metric-samples/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
