import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const endpoint = `/libraries/${params.id}`;

	return {
		tree: fetch(`/libraries/${params.id}/tree`).then((res) => res.json()) ?? {},
		library: await fetch(endpoint).then((res) => res.json())
	};
};
