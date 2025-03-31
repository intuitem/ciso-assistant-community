import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const sm_endpoint = `${BASE_API_URL}/applied-controls/`;
	const ra_endpoint = `${BASE_API_URL}/risk-acceptances/`;
	const task_endpoint = `${BASE_API_URL}/task-nodes/`;

	const res = await fetch(sm_endpoint);
	const applied_controls = await res.json().then((res) => res.results);
	const res2 = await fetch(ra_endpoint);
	const risk_acceptances = await res2.json().then((res) => res.results);
	const res3 = await fetch(task_endpoint);
	const task_nodes = await res3.json().then((res) => res.results);

	return { applied_controls, risk_acceptances, task_nodes };
}) satisfies PageServerLoad;
