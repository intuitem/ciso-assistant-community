import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

const nextMonth = (month: number): string => {
	if (month === 12) {
		return '01';
	}
	return (month + 1).toString().padStart(2, '0');
};

export const load = (async ({ fetch, locals, params }) => {
	const year = params.year;
	const month = params.month.padStart(2, '0');
	const nextMonthStr = nextMonth(parseInt(params.month));
	const nextYear = nextMonthStr === '01' ? parseInt(year) + 1 : parseInt(year);

	const endpoints = {
		appliedControls: `${BASE_API_URL}/applied-controls/?eta__year=${year}&eta__month=${params.month}`,
		riskAcceptances: `${BASE_API_URL}/risk-acceptances/?expiry_date__year=${year}&expiry_date__month=${params.month}`,
		audits: `${BASE_API_URL}/compliance-assessments/?due_date__year=${year}&due_date__month=${params.month}`,
		tasks: `${BASE_API_URL}/task-templates/calendar/${year}-${month}-01/${nextYear}-${nextMonthStr}-01`,
		contracts: `${BASE_API_URL}/contracts/?end_date__year=${year}&end_date__month=${params.month}`,
		securityExceptions: `${BASE_API_URL}/security-exceptions/?expiration_date__year=${year}&expiration_date__month=${params.month}`,
		findings: `${BASE_API_URL}/findings/?due_date__year=${year}&due_date__month=${params.month}`,
		riskAssessments: `${BASE_API_URL}/risk-assessments/?due_date__year=${year}&due_date__month=${params.month}`
	};

	// Fetch actor IDs for the current user (including team memberships)
	const actorIdsPromise = fetch(`${BASE_API_URL}/folders/my_assignments/?include_teams=true`)
		.then((res) => res.json())
		.then((data) => data.actor_ids ?? [])
		.catch(() => []);

	const keys = Object.keys(endpoints) as (keyof typeof endpoints)[];
	const [actorIds, ...results] = await Promise.all([
		actorIdsPromise,
		...keys.map((key) =>
			Promise.resolve(fetch(endpoints[key]).then((res) => res.json())).catch(() => null)
		)
	]);

	const data: Record<string, any[]> = {};
	keys.forEach((key, i) => {
		const result = results[i];
		if (result) {
			// tasks endpoint returns array directly, others return { results: [...] }
			data[key] = key === 'tasks' ? result : (result.results ?? []);
		} else {
			data[key] = [];
		}
	});

	return {
		appliedControls: data.appliedControls,
		riskAcceptances: data.riskAcceptances,
		audits: data.audits,
		tasks: data.tasks,
		contracts: data.contracts,
		securityExceptions: data.securityExceptions,
		findings: data.findings,
		riskAssessments: data.riskAssessments,
		actorIds: actorIds as string[],
		title: 'calendar'
	};
}) satisfies PageServerLoad;
