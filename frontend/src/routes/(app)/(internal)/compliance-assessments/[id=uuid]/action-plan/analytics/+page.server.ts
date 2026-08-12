import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const URLModel = 'compliance-assessments';

	const [assessmentRes, analyticsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/action-plan/budget-overview/${url.search}`)
	]);

	if (!assessmentRes.ok) {
		error(assessmentRes.status, `Failed to load compliance assessment (${assessmentRes.status})`);
	}

	const compliance_assessment = await assessmentRes.json();
	const analytics = analyticsRes.ok ? await analyticsRes.json() : null;

	return {
		URLModel,
		compliance_assessment,
		analytics
	};
};
