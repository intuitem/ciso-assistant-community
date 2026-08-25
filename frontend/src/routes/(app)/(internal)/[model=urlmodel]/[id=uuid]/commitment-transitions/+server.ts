import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// The `[field=fields]` route only matches names that are table columns, and this is
// an action rather than a field — hence its own proxy. It also has to exist here
// rather than being a plain PATCH on `/{model}/{id}`: models whose static route folder
// has no `+server.ts` (task-templates) shadow the generic proxy and answer PATCH with 405.
const endpointFor = (params: { model: string; id: string }) => {
	const model = getModelInfo(params.model);
	return `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/commitment_transitions/`;
};

const forward = async (res: Response) => {
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
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
