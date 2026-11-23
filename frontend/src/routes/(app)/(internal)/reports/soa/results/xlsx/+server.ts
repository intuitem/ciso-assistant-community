import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const complianceAssessmentId = url.searchParams.get('compliance_assessment');
	if (!complianceAssessmentId) {
		error(400, 'Missing compliance_assessment parameter');
	}
	const params = new URLSearchParams({ export: 'xlsx' });
	const riskAssessments = url.searchParams.get('risk_assessments');
	const implementationGroups = url.searchParams.get('implementation_groups');
	if (riskAssessments) params.set('risk_assessment_ids', riskAssessments);
	if (implementationGroups) params.set('implementation_groups', implementationGroups);

	const res = await fetch(
		`${BASE_API_URL}/compliance-assessments/${complianceAssessmentId}/soa/?${params}`
	);
	if (!res.ok) {
		error(res.status, 'Error exporting the Statement of Applicability');
	}
	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition':
				res.headers.get('Content-Disposition') ?? 'attachment; filename="soa.xlsx"'
		}
	});
};
