import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// `[field=fields]` only matches table columns, and a plain PATCH on `/{model}/{id}`
// is shadowed (405) by static route folders without a `+server.ts` — hence its own proxy.
const endpointFor = (params: { model: string; id: string }) => {
	const model = getModelInfo(params.model);
	return `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/commitment_transitions/`;
};

const forward = async (res: Response) => {
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		// Fetched straight from the browser: logout clears cookies, not the cache.
		headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
	});
};

export const GET: RequestHandler = async ({ fetch, params }) =>
	forward(await fetch(endpointFor(params as { model: string; id: string })));

export const POST: RequestHandler = async ({ fetch, params, request }) =>
	forward(
		await fetch(endpointFor(params as { model: string; id: string }), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(await request.json())
		})
	);
