import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'findings-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const findings_assessment = await res.json();
	return { URLModel, findings_assessment };
}) satisfies PageServerLoad;
