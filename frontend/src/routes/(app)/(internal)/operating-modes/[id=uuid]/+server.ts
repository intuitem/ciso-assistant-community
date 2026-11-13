import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';

import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const model = getModelInfo('operating-modes');
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? 'operating-modes'}/${params.id}/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'PATCH',
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
