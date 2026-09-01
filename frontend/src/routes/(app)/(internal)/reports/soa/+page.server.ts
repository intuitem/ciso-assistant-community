import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	// Assessments are picked lazily client-side (server-side search) — only probe
	// the counts here so the empty states can be shown without fetching every row.
	const [complianceAssessmentsCount, riskAssessmentsCount] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/?limit=1`)
			.then((res) => res.json())
			.then((data) => data.count ?? 0),
		fetch(`${BASE_API_URL}/risk-assessments/?limit=1`)
			.then((res) => res.json())
			.then((data) => data.count ?? 0)
	]).catch(() => {
		error(400, 'Error loading compliance assessments');
	});

	return {
		complianceAssessmentsCount,
		riskAssessmentsCount
	};
};
