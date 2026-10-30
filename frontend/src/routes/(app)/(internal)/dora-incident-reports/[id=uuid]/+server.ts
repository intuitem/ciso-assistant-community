import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';

import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

const URL_MODEL = 'dora-incident-reports';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(URL_MODEL);
	const search = url.searchParams.toString();
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${params.id}/${search ? '?' + search : ''}`;

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

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const model = getModelInfo(URL_MODEL);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${params.id}/`;

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
