import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { languageTag } from '$paraglide/runtime';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const URLModel = url.searchParams.has('loaded') ? 'loaded-libraries' : 'stored-libraries';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/tree/`;
	const res = await fetch(endpoint, {
		headers: {
			'Accept-Language': languageTag()
		}
	});

	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.json());

	const tree = await res.json();
	return new Response(JSON.stringify(tree), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
