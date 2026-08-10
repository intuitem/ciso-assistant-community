import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const [graphRes, matrixRes, modelRes] = await Promise.all([
		fetch(`${BASE_API_URL}/threat-models/${params.id}/graph/`),
		fetch(`${BASE_API_URL}/threat-models/${params.id}/matrix/`),
		fetch(`${BASE_API_URL}/threat-models/${params.id}/`)
	]);
	for (const res of [graphRes, matrixRes, modelRes]) {
		if (!res.ok) error(res.status, await res.text());
	}

	return {
		graph: await graphRes.json(),
		matrix: await matrixRes.json(),
		threatModel: await modelRes.json()
	};
};
