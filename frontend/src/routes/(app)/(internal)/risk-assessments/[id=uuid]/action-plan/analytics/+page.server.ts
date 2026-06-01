import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const URLModel = 'risk-assessments';

	const [assessmentRes, analyticsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/action-plan/budget-overview/${url.search}`)
	]);

	if (!assessmentRes.ok) {
		error(assessmentRes.status, `Failed to load risk assessment (${assessmentRes.status})`);
	}

	const risk_assessment = await assessmentRes.json();
	const analytics = analyticsRes.ok ? await analyticsRes.json() : null;

	return {
		URLModel,
		risk_assessment,
		analytics
	};
};
