import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'quantitative-risk-studies';
	const endpoint = `${BASE_API_URL}/crq/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const quantitative_risk_study = await res.json();
	return { URLModel, quantitative_risk_study, title: 'Action Plan' };
}) satisfies PageServerLoad;
