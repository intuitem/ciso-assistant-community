import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// The custom list page shadows [model=urlmodel]/+server.ts, so a fetch() for
// this model gets HTML back — which is what left the catalog autocomplete empty.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const model = getModelInfo('ttp-catalogs');
	const queryParams = url.searchParams.toString();
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? model.urlModel}/${
		queryParams ? '?' + queryParams : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const detail = res.headers.get('content-type')?.includes('application/json')
			? await res.json()
			: await res.text();
		error(res.status as NumericRange<400, 599>, detail);
	}

	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
