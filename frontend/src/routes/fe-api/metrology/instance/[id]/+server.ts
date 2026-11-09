import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// One metric with its definition, unit and target: what a widget preview
// needs to draw it as the dashboard will.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-instances/${params.id}/`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
