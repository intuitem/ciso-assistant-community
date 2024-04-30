import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, params }) => {
	const isLoaded = url.searchParams.has('loaded');
	const URLModel = isLoaded ? 'loaded-libraries' : 'stored-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/?urn=${params.id}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res
		.json()
		.then((res) => res.results)
		.then((res) => res.reduce((acc, curr) => (acc.version > curr.version ? acc : curr))); // Get the latest version of the library

	const uuid = data.id;
	const contentEndpoint = `${BASE_API_URL}/${URLModel}/${uuid}/content`;
	const contentRes = await fetch(contentEndpoint);
	if (!contentRes.ok) {
		error(contentRes.status as NumericRange<400, 599>, await contentRes.json());
	}
	const content = await contentRes.json();
	data.objects = content;
	if (!isLoaded) {
		data.objects = JSON.parse(content);
	}

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
