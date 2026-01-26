import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

function buildMultiParam(key: string, values: string[]): string {
	if (!values || values.length === 0) return '';
	return values.map((v) => `${key}=${v}`).join('&');
}

function buildEndpoint(base: string, filterParams: string, extraParams: string = ''): string {
	const params = [filterParams, extraParams].filter(Boolean).join('&');
	return params ? `${base}?${params}` : base;
}

export const load: PageServerLoad = async ({ fetch, parent, url }) => {
	const { user } = await parent();
	const includeTeams = url.searchParams.get('include_teams') === 'true';

	const res = await fetch(`${BASE_API_URL}/folders/my_assignments/?include_teams=${includeTeams}`);
	const data = await res.json();

	// Actor IDs from backend ensure consistency with backend filtering
	const actorIds: string[] = data.actor_ids || [];

	const ownerParams = buildMultiParam('owner', actorIds);
	const ownersParams = buildMultiParam('owners', actorIds);
	const authorsParams = buildMultiParam('authors', actorIds);
	const assignedToParams = buildMultiParam('assigned_to', actorIds);

	const countEndpoints: Record<string, string> = {
		appliedControls: buildEndpoint('/applied-controls', ownerParams, 'limit=0'),
		tasks: buildEndpoint('/task-templates', assignedToParams, 'limit=0'),
		complianceAssessments: buildEndpoint('/compliance-assessments', authorsParams, 'limit=0'),
		riskAssessments: buildEndpoint('/risk-assessments', authorsParams, 'limit=0'),
		riskScenarios: buildEndpoint('/risk-scenarios', ownerParams, 'limit=0'),
		incidents: buildEndpoint('/incidents', ownersParams, 'limit=0'),
		securityExceptions: buildEndpoint('/security-exceptions', ownersParams, 'limit=0'),
		findingsAssessments: buildEndpoint('/findings-assessments', authorsParams, 'limit=0'),
		findings: buildEndpoint('/findings', ownerParams, 'limit=0'),
		organisationObjectives: buildEndpoint('/organisation-objectives', assignedToParams, 'limit=0'),
		rightRequests: buildEndpoint('/privacy/right-requests', ownerParams, 'limit=0'),
		validationFlows: `/validation-flows?approver=${user.id}&limit=0`,
		metricInstances: buildEndpoint('/metrology/metric-instances', ownerParams, 'limit=0')
	};

	const countsPromise = Promise.all(
		Object.entries(countEndpoints).map(async ([key, endpoint]) => {
			try {
				const countRes = await fetch(`${BASE_API_URL}${endpoint}`);
				const countData = await countRes.json();
				return [key, countData.count || 0] as const;
			} catch {
				return [key, 0] as const;
			}
		})
	).then((entries) => Object.fromEntries(entries) as Record<string, number>);

	return {
		data,
		user,
		includeTeams,
		actorIds,
		title: m.myAssignments(),
		stream: {
			counts: countsPromise
		}
	};
};
