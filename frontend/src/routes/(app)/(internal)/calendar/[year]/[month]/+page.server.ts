import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, locals }) => {
	const appliedControlsEndpoint = `${BASE_API_URL}/applied-controls/`;
	const riskAcceptancesEndpoint = `${BASE_API_URL}/risk-acceptances/`;
	const tasksEndpoint = `${BASE_API_URL}/users/${locals.user.id}/tasks/`;

	const appliedControlsResponse = await fetch(appliedControlsEndpoint);
	const appliedControls = await appliedControlsResponse.json().then((res) => res.results);

	const riskAcceptancesResponse = await fetch(riskAcceptancesEndpoint);
	const riskAcceptances = await riskAcceptancesResponse.json().then((res) => res.results);

	const tasksResponse = await fetch(tasksEndpoint);
	const tasks = await tasksResponse.json();

	return {
		appliedControls,
		riskAcceptances,
		tasks
	};
}) satisfies PageServerLoad;
