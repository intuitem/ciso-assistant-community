import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const complianceAssessmentId = url.searchParams.get('compliance_assessment');
	if (!complianceAssessmentId) {
		error(400, 'Missing compliance_assessment parameter');
	}

	const riskAssessments = url.searchParams.get('risk_assessments') || '';

	let soaUrl = `${BASE_API_URL}/compliance-assessments/${complianceAssessmentId}/soa/`;
	if (riskAssessments) {
		soaUrl += `?risk_assessment_ids=${riskAssessments}`;
	}

	const res = await fetch(soaUrl);
	if (!res.ok) {
		error(res.status, 'Error loading Statement of Applicability data');
	}

	const soaData = await res.json();

	return {
		soaData
	};
};
