import { BASE_API_URL } from '#lib/utils/constants.js';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const URLModel = 'loaded-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/tree/`;
	const res = await fetch(endpoint);

	if (!res.ok) error(res.status, await res.json());

	const tree = await res.json();
	return new Response(JSON.stringify(tree), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
