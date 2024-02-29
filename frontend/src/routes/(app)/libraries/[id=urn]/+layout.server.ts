import { BASE_API_URL } from '$lib/utils/constants';

import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/libraries/${params.id}/`;

	return {
		tree: fetch(`${BASE_API_URL}/libraries/${params.id}/tree`).then((res) => res.json()) ?? {},
		library: await fetch(endpoint).then((res) => res.json())
	};
};
