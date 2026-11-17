import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const params = url.searchParams.toString();
	const endpoint = `${BASE_API_URL}/folders/org_tree/${params ? '?' + params : ''}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		headers: { 'Content-Type': 'application/json' }
	});
};
