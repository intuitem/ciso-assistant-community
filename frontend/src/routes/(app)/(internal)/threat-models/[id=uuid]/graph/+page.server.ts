import { BASE_API_URL } from '#lib/utils/constants.js';
import { discardBody } from '#lib/utils/responses.js';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const [graphRes, matrixRes, modelRes] = await Promise.all([
		fetch(`${BASE_API_URL}/threat-models/${params.id}/graph/`),
		fetch(`${BASE_API_URL}/threat-models/${params.id}/matrix/`),
		fetch(`${BASE_API_URL}/threat-models/${params.id}/`)
	]);
	const responses = [graphRes, matrixRes, modelRes];
	const failed = responses.find((res) => !res.ok);
	if (failed) {
		await discardBody(...responses.filter((res) => res !== failed));
		error(failed.status, await failed.text());
	}

	return {
		graph: await graphRes.json(),
		matrix: await matrixRes.json(),
		threatModel: await modelRes.json()
	};
};
