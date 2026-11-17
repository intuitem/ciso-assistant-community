import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { errorFromBody } from '#lib/utils/errors.js';
import type { RequestHandler } from './$types';

// The object's write data: its related fields hold the ids of every linked object,
// where the read data masks the ones the user cannot see. An editor that sends a
// list of links back starts from it.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/object/`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
