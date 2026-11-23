import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// Readable definitions whose name contains the one being typed: the hint
// under a new metric's name.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/similar/${url.search}`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
