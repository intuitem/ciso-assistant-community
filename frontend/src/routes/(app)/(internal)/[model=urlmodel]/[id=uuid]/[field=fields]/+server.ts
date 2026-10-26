import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/`;

	const body = await request.json();

	const payload: Record<string, any> = {};
	payload[params.field] = body[params.field];

	const res = await fetch(endpoint, { method: 'PATCH', body: JSON.stringify(payload) });
	if (!res.ok) {
		error(res.status, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/${params.field}/${
		url.search || ''
	}`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
