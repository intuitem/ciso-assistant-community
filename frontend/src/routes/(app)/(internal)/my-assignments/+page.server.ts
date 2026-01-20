import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch, parent, url }) => {
	// Get user info from parent layout
	const { user } = await parent();

	// Check if team assignments should be included
	const includeTeams = url.searchParams.get('include_teams') === 'true';

	// Build actor IDs parameter for queries
	// When include_teams is true, use all_actor_ids (user + team actors)
	// Otherwise, use only the user's direct actor_id
	const actorIds: string[] = includeTeams ? user.all_actor_ids : [user.actor_id];
	const actorIdsParam = actorIds.join(',');

	const endpoint = `${BASE_API_URL}/folders/my_assignments/?include_teams=${includeTeams}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	// Fetch counts for each section to determine which ones are empty
	// For Actor-based fields (owner, authors, owners), use actorIdsParam
	// For User-based fields (assigned_to, approver), use user.id only
	const countEndpoints = {
		appliedControls: `/applied-controls?owner=${actorIdsParam}&limit=0`,
		tasks: `/task-templates?assigned_to=${user.id}&limit=0`,
		complianceAssessments: `/compliance-assessments?authors=${actorIdsParam}&limit=0`,
		riskAssessments: `/risk-assessments?authors=${actorIdsParam}&limit=0`,
		riskScenarios: `/risk-scenarios?owner=${actorIdsParam}&limit=0`,
		incidents: `/incidents?owners=${actorIdsParam}&limit=0`,
		securityExceptions: `/security-exceptions?owners=${actorIdsParam}&limit=0`,
		findingsAssessments: `/findings-assessments?authors=${actorIdsParam}&limit=0`,
		findings: `/findings?owner=${actorIdsParam}&limit=0`,
		organisationObjectives: `/organisation-objectives?assigned_to=${user.id}&limit=0`,
		rightRequests: `/privacy/right-requests?owner=${actorIdsParam}&limit=0`,
		validationFlows: `/validation-flows?approver=${user.id}&limit=0`,
		metricInstances: `/metrology/metric-instances?owner=${actorIdsParam}&limit=0`
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

	return { data, counts, user, includeTeams, title: m.myAssignments() };
}) satisfies PageServerLoad;
