import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const complianceAssessmentId = url.searchParams.get('compliance_assessment');
	if (!complianceAssessmentId) {
		error(400, 'Missing compliance_assessment parameter');
	}

	const riskAssessments = url.searchParams.get('risk_assessments') || '';
	const implementationGroups = url.searchParams.get('implementation_groups') || '';

	const params = new URLSearchParams();
	if (riskAssessments) {
		params.set('risk_assessment_ids', riskAssessments);
	}
	if (implementationGroups) {
		params.set('implementation_groups', implementationGroups);
	}

	const queryString = params.toString();
	const soaUrl = `${BASE_API_URL}/compliance-assessments/${complianceAssessmentId}/soa/${queryString ? `?${queryString}` : ''}`;

	const res = await fetch(soaUrl);
	if (!res.ok) {
		error(res.status, 'Error loading Statement of Applicability data');
	}

	const soaData = await res.json();

	return {
		soaData
	};
};
