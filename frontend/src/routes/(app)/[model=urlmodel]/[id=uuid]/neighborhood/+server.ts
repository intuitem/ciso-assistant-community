import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const model = getModelInfo(params.model as string);
	const res = await fetch(
		`${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/neighborhood/`
	);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, 'Could not load the relations of this object');
	}
	return new Response(JSON.stringify(await res.json()), {
		// Fetched from the browser: logout clears cookies, not the cache.
		headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
	});
};
