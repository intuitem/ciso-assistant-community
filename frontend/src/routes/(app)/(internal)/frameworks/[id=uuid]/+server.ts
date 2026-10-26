import type { RequestHandler } from './$types';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = `${BASE_API_URL}/frameworks/${params.id}/${
		url.searchParams ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
