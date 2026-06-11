import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const baseUrl = `${BASE_API_URL}/${model.endpointUrl ? model.endpointUrl : params.model}`;

	// Fetch options needed for batch creation (e.g. category, deletion_policy)
	const allowedOptions = new Set(['category', 'deletion_policy']);
	const optionsField = url.searchParams.get('options');
	if (!optionsField || !allowedOptions.has(optionsField)) {
		error(400, { message: 'Invalid or missing options parameter' });
	}

	const endpoint = `${baseUrl}/${encodeURIComponent(optionsField)}/`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		headers: { 'Content-Type': 'application/json' }
	});
};

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ? model.endpointUrl : params.model}/batch-create/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
