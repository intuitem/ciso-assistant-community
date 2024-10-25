import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/plan/`;

	const res = await fetch(endpoint);
	const risk_assessment = await res.json();
	return { URLModel, risk_assessment };
}) satisfies PageServerLoad;
