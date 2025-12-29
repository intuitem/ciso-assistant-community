import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = new URL(
		`${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.filter}/`
	);
	endpoint.search = url.searchParams.toString();

	const res = await fetch(endpoint.toString());
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const optionsResponse = await res.json();
	if (params.filter === 'names') {
		return new Response(JSON.stringify(optionsResponse), {
			headers: {
				'Content-Type': 'application/json'
			}
		});
	}

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
