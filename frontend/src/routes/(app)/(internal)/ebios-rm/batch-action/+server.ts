import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const model = getModelInfo('ebios-rm');
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/batch-action/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	});

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
