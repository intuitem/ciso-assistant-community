import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const URLModel = 'risk-assessments';

	const [assessmentRes, analyticsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/action-plan/analytics/${url.search}`)
	]);

	const risk_assessment = await assessmentRes.json();
	const analytics = analyticsRes.ok ? await analyticsRes.json() : null;

	return {
		URLModel,
		risk_assessment,
		analytics,
		title: 'Action plan analytics'
	};
};
