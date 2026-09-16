import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// fetch() does not reject on 4xx, so an unchecked count turns a 403 into an
// empty state.
const probeCount = async (fetchFn: typeof fetch, endpoint: string, label: string) => {
	const res = await fetchFn(`${BASE_API_URL}/${endpoint}/?limit=1`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, `Error loading ${label}`);
	}
	return (await res.json()).count ?? 0;
};

export const load: PageServerLoad = async ({ fetch }) => {
	// Assessments are picked lazily client-side (server-side search) — only probe
	// the counts here so the empty states can be shown without fetching every row.
	const [complianceAssessmentsCount, riskAssessmentsCount] = await Promise.all([
		probeCount(fetch, 'compliance-assessments', 'compliance assessments'),
		probeCount(fetch, 'risk-assessments', 'risk assessments')
	]);

	return {
		complianceAssessmentsCount,
		riskAssessmentsCount
	};
};
