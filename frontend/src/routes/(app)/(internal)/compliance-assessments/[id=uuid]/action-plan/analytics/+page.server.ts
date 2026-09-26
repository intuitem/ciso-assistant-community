import { BASE_API_URL } from '$lib/utils/constants';
import { discardBody } from '$lib/utils/responses';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const URLModel = 'compliance-assessments';

	const [assessmentRes, analytics] = await Promise.all([
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`),
		fetch(
			`${BASE_API_URL}/${URLModel}/${params.id}/action-plan/budget-overview/${url.search}`
		).then((res) => (res.ok ? res.json() : discardBody(res).then(() => null)))
	]);

	if (!assessmentRes.ok) {
		await discardBody(assessmentRes);
		error(assessmentRes.status, `Failed to load compliance assessment (${assessmentRes.status})`);
	}

	const compliance_assessment = await assessmentRes.json();

	return {
		URLModel,
		compliance_assessment,
		analytics
	};
};
