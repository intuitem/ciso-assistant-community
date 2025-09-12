import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/content-types/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
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
