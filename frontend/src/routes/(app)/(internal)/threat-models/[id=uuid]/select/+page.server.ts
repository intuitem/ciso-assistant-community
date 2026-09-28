import { BASE_API_URL } from '$lib/utils/constants';
import { discardBody } from '$lib/utils/responses';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const [matrixRes, modelRes] = await Promise.all([
		fetch(`${BASE_API_URL}/threat-models/${params.id}/matrix/`),
		fetch(`${BASE_API_URL}/threat-models/${params.id}/`)
	]);
	if (!matrixRes.ok) {
		await discardBody(modelRes);
		error(matrixRes.status, await matrixRes.text());
	}
	if (!modelRes.ok) {
		await discardBody(matrixRes);
		error(modelRes.status, await modelRes.text());
	}

	return { matrix: await matrixRes.json(), threatModel: await modelRes.json() };
};
