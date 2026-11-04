import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const model = getModelInfo(params.model as string);
	const res = await fetch(
		`${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/x-rays/`
	);
	if (!res.ok) {
		error(res.status, 'Could not load the X-rays of this object');
	}
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
	});
};
