import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entity-assessments/metrics/`;

	const [res, tiersRes] = await Promise.all([
		fetch(endpoint),
		fetch(`${BASE_API_URL}/tiers/?ordering=-rank`)
	]);
	const data = await res.json();
	const tiers = tiersRes.ok ? ((await tiersRes.json()).results ?? []) : [];

	return { data, tiers, title: m.tprmOverview() };
}) satisfies PageServerLoad;
