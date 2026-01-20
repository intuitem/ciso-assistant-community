import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

// Helper to build query params with multiple values for the same key
// e.g., buildMultiParam('owner', ['id1', 'id2']) => 'owner=id1&owner=id2'
function buildMultiParam(key: string, values: string[]): string {
	return values.map((v) => `${key}=${v}`).join('&');
}

export const load = (async ({ fetch, parent, url }) => {
	// Get user info from parent layout
	const { user } = await parent();

	// Check if team assignments should be included
	const includeTeams = url.searchParams.get('include_teams') === 'true';

	// Build actor IDs for queries
	// When include_teams is true, use all_actor_ids (user + team actors)
	// Otherwise, use only the user's direct actor_id
	const actorIds: string[] = includeTeams ? user.all_actor_ids : [user.actor_id];

	// Return promises for streaming - page renders immediately while data loads
	const dashboardDataPromise = fetch(
		`${BASE_API_URL}/folders/my_assignments/?include_teams=${includeTeams}`
	).then((res) => res.json());

	// Function to fetch count for a single endpoint
	const fetchCount = async (endpoint: string): Promise<number> => {
		try {
			const res = await fetch(`${BASE_API_URL}${endpoint}`);
			const data = await res.json();
			return data.count || 0;
		} catch (error) {
			console.error(`Error fetching count for ${endpoint}:`, error);
			return 0;
		}
	};

	// Create promises for all counts
	const countsPromise = (async () => {
		// Build proper query params with multiple values (owner=id1&owner=id2)
		const ownerParam = buildMultiParam('owner', actorIds);
		const ownersParam = buildMultiParam('owners', actorIds);
		const authorsParam = buildMultiParam('authors', actorIds);

		const countEndpoints = {
			appliedControls: `/applied-controls?${ownerParam}&limit=0`,
			tasks: `/task-templates?assigned_to=${user.id}&limit=0`,
			complianceAssessments: `/compliance-assessments?${authorsParam}&limit=0`,
			riskAssessments: `/risk-assessments?${authorsParam}&limit=0`,
			riskScenarios: `/risk-scenarios?${ownerParam}&limit=0`,
			incidents: `/incidents?${ownersParam}&limit=0`,
			securityExceptions: `/security-exceptions?${ownersParam}&limit=0`,
			findingsAssessments: `/findings-assessments?${authorsParam}&limit=0`,
			findings: `/findings?${ownerParam}&limit=0`,
			organisationObjectives: `/organisation-objectives?assigned_to=${user.id}&limit=0`,
			rightRequests: `/privacy/right-requests?${ownerParam}&limit=0`,
			validationFlows: `/validation-flows?approver=${user.id}&limit=0`,
			metricInstances: `/metrology/metric-instances?${ownerParam}&limit=0`
		};

		const counts: Record<string, number> = {};

		// Fetch all counts in parallel
		await Promise.all(
			Object.entries(countEndpoints).map(async ([key, endpoint]) => {
				counts[key] = await fetchCount(endpoint);
			})
		);

		return counts;
	})();

	// Return immediately with promises - SvelteKit will stream the results
	return {
		user,
		includeTeams,
		actorIds, // Pass array for building query params in frontend
		title: m.myAssignments(),
		// Streamed data (returned as promises)
		streamed: {
			dashboardData: dashboardDataPromise,
			counts: countsPromise
		}
	};
}) satisfies PageServerLoad;
