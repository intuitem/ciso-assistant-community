import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/${params.model}/${params.filter}/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const optionsResponse = await res.json();

	const options = Object.keys(optionsResponse)
		.map((key) => ({
			label: optionsResponse[key],
			value: key
		}))
		.sort((a, b) => a.label.localeCompare(b.label));

	return new Response(JSON.stringify(options), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
