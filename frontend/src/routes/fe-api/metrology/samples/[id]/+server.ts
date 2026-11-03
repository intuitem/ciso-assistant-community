import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// The entered values of one metric, newest first: what a widget preview draws.
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const limit = url.searchParams.get('limit') ?? '200';
	const res = await fetch(
		`${BASE_API_URL}/metrology/custom-metric-samples/?metric_instance=${params.id}&ordering=-timestamp&limit=${limit}`
	);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
