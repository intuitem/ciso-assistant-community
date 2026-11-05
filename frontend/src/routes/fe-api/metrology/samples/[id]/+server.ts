import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// The entered values of one metric, newest first: what a widget preview draws.
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	// A number, or the default: nothing from the query string reaches the
	// upstream URL as text.
	const limit = Math.min(
		Math.max(parseInt(url.searchParams.get('limit') ?? '', 10) || 200, 1),
		1000
	);
	const query = new URLSearchParams({
		metric_instance: params.id,
		ordering: '-timestamp',
		limit: String(limit)
	});
	const res = await fetch(`${BASE_API_URL}/metrology/custom-metric-samples/?${query}`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
