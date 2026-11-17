import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const model = getModelInfo('service-accounts');
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${url.search}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
