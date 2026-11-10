import { BASE_API_URL } from '#lib/utils/constants.js';
import { errorFromBody } from '#lib/utils/errors.js';
import type { RequestHandler } from './$types';

// The page shadows the generic list proxy: option lists still fetch JSON here.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const res = await fetch(`${BASE_API_URL}/terminologies/?${url.searchParams.toString()}`);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
