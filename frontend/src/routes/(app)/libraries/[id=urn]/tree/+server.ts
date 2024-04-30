import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const URLModel = url.searchParams.has('loaded') ? 'loaded-libraries' : 'stored-libraries';
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
	const treeEndpoint = `${BASE_API_URL}/${URLModel}/${uuid}/tree`;
	const treeRes = await fetch(treeEndpoint);
	if (!treeRes.ok) {
		error(treeRes.status as NumericRange<400, 599>, await treeRes.json());
	}

	const tree = await treeRes.json();

	return new Response(JSON.stringify(tree), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
