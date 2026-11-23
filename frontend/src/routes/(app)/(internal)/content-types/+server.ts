import type { RequestHandler } from './$types';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/content-types/${
		url.searchParams.size ? '?' + url.searchParams.toString() : ''
	}`;

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
