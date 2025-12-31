import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch, parent }) => {
	// Get user info from parent layout
	const { user } = await parent();
	const userId = user.id;

	const endpoint = `${BASE_API_URL}/folders/my_assignments/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	// Fetch counts for each section to determine which ones are empty
	const countEndpoints = {
		appliedControls: `/applied-controls?owner=${userId}&limit=0`,
		tasks: `/task-templates?assigned_to=${userId}&limit=0`,
		complianceAssessments: `/compliance-assessments?authors=${userId}&limit=0`,
		riskAssessments: `/risk-assessments?authors=${userId}&limit=0`,
		riskScenarios: `/risk-scenarios?owner=${userId}&limit=0`,
		incidents: `/incidents?owners=${userId}&limit=0`,
		securityExceptions: `/security-exceptions?owners=${userId}&limit=0`,
		findingsAssessments: `/findings-assessments?authors=${userId}&limit=0`,
		findings: `/findings?owner=${userId}&limit=0`,
		organisationObjectives: `/organisation-objectives?assigned_to=${userId}&limit=0`,
		rightRequests: `/privacy/right-requests?owner=${userId}&limit=0`,
		validationFlows: `/validation-flows?approver=${userId}&limit=0`,
		metricInstances: `/metrology/metric-instances?owner=${userId}&limit=0`
	};

	const counts: Record<string, number> = {};

	// Fetch all counts in parallel
	await Promise.all(
		Object.entries(countEndpoints).map(async ([key, endpoint]) => {
			try {
				const countRes = await fetch(`${BASE_API_URL}${endpoint}`);
				const countData = await countRes.json();
				counts[key] = countData.count || 0;
			} catch (error) {
				console.error(`Error fetching count for ${key}:`, error);
				counts[key] = 0;
			}
		})
	);

	return { data, counts, user, title: m.myAssignments() };
}) satisfies PageServerLoad;
