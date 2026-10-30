import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const model = getModelInfo('service-accounts');
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${params.id}/rotate-secret/`;

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
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
