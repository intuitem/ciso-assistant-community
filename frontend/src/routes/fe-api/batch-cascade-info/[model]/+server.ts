import { BASE_API_URL } from '#lib/utils/constants.js';
import { URL_MODEL_MAP } from '#lib/utils/crud.js';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import type { urlModel } from '#lib/utils/types.js';

export const POST: RequestHandler = async ({ params, fetch, request }) => {
	const modelConfig = URL_MODEL_MAP[params.model as urlModel];
	const apiPath = modelConfig?.endpointUrl ?? params.model;
	const { ids } = await request.json();

	const response = await fetch(`${BASE_API_URL}/${apiPath}/batch-cascade-info/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ ids })
	});

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return json(await response.json());
};
