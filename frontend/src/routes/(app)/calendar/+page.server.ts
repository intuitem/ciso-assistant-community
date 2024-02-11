import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const sm_endpoint = `${BASE_API_URL}/security-measures/`;
	const ra_endpoint = `${BASE_API_URL}/risk-acceptances/`;

	const res = await fetch(sm_endpoint);
	const security_measures = await res.json().then((res) => res.results);
	const res2 = await fetch(ra_endpoint);
	const risk_acceptances = await res2.json().then((res) => res.results);

	return { security_measures, risk_acceptances };
}) satisfies PageServerLoad;
