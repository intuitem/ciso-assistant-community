import type { RequestHandler } from './$types';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.filter}/${url.search}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	const optionsResponse = await res.json();

	const options =
		typeof Object.values(optionsResponse)[0] === 'string'
			? Object.keys(optionsResponse).map((key) => ({
					label: optionsResponse[key],
					value: key
				}))
			: optionsResponse;

	return new Response(JSON.stringify(options), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
