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
	const filterActorIds = url.searchParams.getAll('actor');

	let actorIds: string[] = [];
	let filterActorLabels: string[] = [];
	let approverUserIds: string[] = []; // User IDs for validation flows (approver is User FK, not Actor)
	let data: any;

	if (filterActorIds.length > 0) {
		// Filter by specific actors - fetch actor details for labels and user IDs
		actorIds = filterActorIds;
		// Fetch details for each actor
		await Promise.all(
			filterActorIds.map(async (actorId) => {
				try {
					const actorRes = await fetch(`${BASE_API_URL}/actors/${actorId}/`);
					if (actorRes.ok) {
						const actorData = await actorRes.json();
						filterActorLabels.push(actorData.str || actorData.name || actorId);

						// Extract user IDs for validation flows approver filter
						// Note: ActorReadSerializer returns 'specific' field (not 'user' or 'team')
						if (actorData.type === 'user' && actorData.specific?.id) {
							approverUserIds.push(actorData.specific.id);
						} else if (actorData.type === 'team' && actorData.specific?.id) {
							// For teams, fetch team members to get their user IDs
							try {
								const teamRes = await fetch(`${BASE_API_URL}/teams/${actorData.specific.id}/`);
								if (teamRes.ok) {
									const teamData = await teamRes.json();
									// Add leader, deputies, and members
									if (teamData.leader?.id) approverUserIds.push(teamData.leader.id);
									teamData.deputies?.forEach((d: { id: string }) => {
										if (d.id) approverUserIds.push(d.id);
									});
									teamData.members?.forEach((m: { id: string }) => {
										if (m.id) approverUserIds.push(m.id);
									});
								}
							} catch {
								// If team fetch fails, continue
							}
						}
					}
				} catch {
					// If actor fetch fails, use the ID as label
					filterActorLabels.push(actorId);
				}
			})
		);
		// Deduplicate user IDs
		approverUserIds = [...new Set(approverUserIds)];
		// Still fetch my_assignments for metrics display
		const res = await fetch(
			`${BASE_API_URL}/folders/my_assignments/?include_teams=${includeTeams}`
		);
		data = await res.json();
	} else {
		// Default: current user's assignments
		const res = await fetch(
			`${BASE_API_URL}/folders/my_assignments/?include_teams=${includeTeams}`
		);
		data = await res.json();
		// Actor IDs from backend ensure consistency with backend filtering
		actorIds = data.actor_ids || [];
		// For validation flows, use current user's ID
		approverUserIds = [user.id];
	}

	const ownerParams = buildMultiParam('owner', actorIds);
	const ownersParams = buildMultiParam('owners', actorIds);
	const authorsParams = buildMultiParam('authors', actorIds);
	const assignedToParams = buildMultiParam('assigned_to', actorIds);
	const approverParams = buildMultiParam('approver', approverUserIds);

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
		validationFlows: buildEndpoint('/validation-flows', approverParams, 'limit=0'),
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
		approverUserIds,
		filterActorIds,
		filterActorLabels,
		title: m.myAssignments(),
		stream: {
			counts: countsPromise
		}
	};
};
