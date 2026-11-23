import { BASE_API_URL } from '#lib/utils/constants.js';
import { selectionParams, withParams } from '#lib/utils/scenarioSelection.js';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params, url }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [res, selectionRes] = await Promise.all([
		fetch(endpoint),
		fetch(
			withParams(
				`${BASE_API_URL}/${URLModel}/${params.id}/scenario-selection/`,
				selectionParams(url.searchParams)
			)
		)
	]);
	const risk_assessment = await res.json();
	return {
		URLModel,
		risk_assessment,
		selection: selectionRes.ok ? await selectionRes.json() : null,
		selectionError: !selectionRes.ok
	};
}) satisfies PageServerLoad;
