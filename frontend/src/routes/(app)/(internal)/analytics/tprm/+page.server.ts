import { BASE_API_URL } from '$lib/utils/constants';

import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entity-assessments/metrics/`;

	const [res, tiersRes, entitiesRes] = await Promise.all([
		fetch(endpoint),
		fetch(`${BASE_API_URL}/tiers/?ordering=-rank`),
		fetch(`${BASE_API_URL}/entities/?limit=1`)
	]);
	const data = await res.json();
	const tiers = tiersRes.ok ? ((await tiersRes.json()).results ?? []) : [];
	const entitiesCount = entitiesRes.ok ? ((await entitiesRes.json()).count ?? 0) : 0;

	return { data, tiers, entitiesCount, title: m.tprmOverview() };
}) satisfies PageServerLoad;
