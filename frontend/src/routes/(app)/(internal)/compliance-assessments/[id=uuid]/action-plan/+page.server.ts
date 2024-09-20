import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const actionPlanEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/action_plan/`;

	const res = await fetch(endpoint);
	const actionPlanRes = await fetch(actionPlanEndpoint);
	const compliance_assessment = await res.json();
	const actionPlan = await actionPlanRes.json();
	return { URLModel, compliance_assessment, actionPlan };
}) satisfies PageServerLoad;
