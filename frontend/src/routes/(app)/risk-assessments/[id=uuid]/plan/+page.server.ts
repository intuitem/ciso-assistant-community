import { BASE_API_URL } from '$lib/utils/constants';
import type { UUID } from 'crypto';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/plan/`;

	const res = await fetch(endpoint);
	const risk_assessment = await res.json();
	const folder = await fetch(`${BASE_API_URL}/folders/${risk_assessment.project.id.folder}/`).then(
		(res) => res.json()
	);

	risk_assessment.folder = folder;

	return { URLModel, risk_assessment };
}) satisfies PageServerLoad;
