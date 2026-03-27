import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const [complianceRes, riskRes] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/?ordering=-created_at`),
		fetch(`${BASE_API_URL}/risk-assessments/?ordering=-created_at`)
	]);

	if (!complianceRes.ok) {
		error(400, 'Error loading compliance assessments');
	}
	if (!riskRes.ok) {
		error(400, 'Error loading risk assessments');
	}

	const complianceData = await complianceRes.json();
	const riskData = await riskRes.json();

	return {
		complianceAssessments: complianceData.results ?? complianceData,
		riskAssessments: riskData.results ?? riskData
	};
};
