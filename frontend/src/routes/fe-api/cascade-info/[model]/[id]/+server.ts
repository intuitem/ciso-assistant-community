import { BASE_API_URL } from '$lib/utils/constants';
import { URL_MODEL_MAP } from '$lib/utils/crud';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import type { urlModel } from '$lib/utils/types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const { model, id } = params;

	// Use the endpointUrl from URL_MODEL_MAP if available, otherwise use the model directly
	const modelConfig = URL_MODEL_MAP[model as urlModel];
	const apiPath = modelConfig?.endpointUrl ?? model;

	const endpoint = `${BASE_API_URL}/${apiPath}/${id}/cascade-info/`;
	const response = await fetch(endpoint);

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return json(await response.json());
};
