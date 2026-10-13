import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

// One metric definition, for the compose modal's "use the levels of" picker
// and the formula drawer: the generic detail route addresses the API by URL
// model, not by its path.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/${params.id}/`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

// The formula drawer saves a definition's formula alone: the API checks the
// right to change it and validates the formula.
export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
