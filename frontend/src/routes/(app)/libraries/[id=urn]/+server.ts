import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, params }) => {
	const isLoaded = url.searchParams.has('loaded');
	const URLModel = isLoaded ? 'loaded-libraries' : 'stored-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const contentEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/content`;

	const [res,contentRes] = await Promise.all([
		fetch(endpoint),
		fetch(contentEndpoint)
	]);

	if (!res.ok)
		error(res.status as NumericRange<400, 599>, await res.json());
	if (!contentRes.ok)
		error(contentRes.status as NumericRange<400, 599>, await contentRes.json());

	const data = await res.json()
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
