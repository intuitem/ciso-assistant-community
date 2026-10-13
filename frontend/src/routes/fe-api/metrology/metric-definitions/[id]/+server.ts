import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

// One metric definition, for the compose modal's "use the levels of" picker:
// the generic detail route addresses the API by URL model, not by its path.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/${params.id}/`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
