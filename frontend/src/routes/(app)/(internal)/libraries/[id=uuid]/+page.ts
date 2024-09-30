import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const endpoint = `/libraries/${params.id}`;
	const queryParams = url.searchParams.toString();

	return {
		tree: fetch(`${endpoint}/tree?${queryParams}`).then((res) => res.json()) ?? {},
		library: await fetch(`${endpoint}?${queryParams}`).then((res) => res.json())
	};
};
