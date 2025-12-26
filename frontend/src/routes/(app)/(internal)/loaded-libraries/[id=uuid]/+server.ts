import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, params }) => {
	const URLModel = 'loaded-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const contentEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/content/`;
	const relatedObjectsEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/related-objects/`;

	const [res, contentRes, relatedObjectsRes] = await Promise.all([
		fetch(endpoint),
		fetch(contentEndpoint),
		fetch(relatedObjectsEndpoint)
	]);

	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.json());
	if (!contentRes.ok) error(contentRes.status as NumericRange<400, 599>, await contentRes.json());
	if (!relatedObjectsRes.ok)
		error(relatedObjectsRes.status as NumericRange<400, 599>, await relatedObjectsRes.json());

	const data = await res.json();
	const content = await contentRes.json();
	const relatedObjects = await relatedObjectsRes.json();
	data.objects = content;
	data.relatedObjects = relatedObjects;

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
