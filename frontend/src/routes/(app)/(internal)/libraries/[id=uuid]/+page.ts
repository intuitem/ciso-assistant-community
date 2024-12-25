import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const endpoint = `/libraries/${params.id}`;
	const queryParams = url.searchParams.toString();
	const library = await fetch(`${endpoint}?${queryParams}`).then((res) => res.json());

	return {
		tree: fetch(`${endpoint}/tree?${queryParams}`).then((res) => res.json()) ?? {},
		library,
		title: library.name
	};
};
