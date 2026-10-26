import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// ebios-rm is left out of URL_MODEL, so the generic [model=urlmodel] proxy never matches it.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const model = getModelInfo('ebios-rm');
	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/autocomplete/${url.search}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
