import { BASE_API_URL } from '#lib/utils/constants.js';
import { discardBody } from '#lib/utils/responses.js';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, params }) => {
	const URLModel = 'loaded-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const contentEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/content/`;

	const [res, contentRes] = await Promise.all([fetch(endpoint), fetch(contentEndpoint)]);

	if (!res.ok) {
		await discardBody(contentRes);
		error(res.status, await res.json());
	}
	if (!contentRes.ok) {
		await discardBody(res);
		error(contentRes.status, await contentRes.json());
	}

	const data = await res.json();
	const content = await contentRes.json();
	data.objects = content;

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
