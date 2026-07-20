import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const [complianceAssessments, riskAssessments] = await Promise.all([
		fetchAllPages(fetch, `${BASE_API_URL}/compliance-assessments/?ordering=-created_at`),
		fetchAllPages(fetch, `${BASE_API_URL}/risk-assessments/?ordering=-created_at`)
	]);

	// Fetch implementation_groups_definition for each unique framework
	const frameworkIds = [
		...new Set(
			complianceAssessments.map((ca: Record<string, any>) => ca.framework?.id).filter(Boolean)
		)
	];

	const frameworkGroupsMap: Record<string, any[]> = {};
	if (frameworkIds.length > 0) {
		const frameworkResponses = await Promise.all(
			frameworkIds.map((id: string) => fetch(`${BASE_API_URL}/frameworks/${id}/`))
		);
		for (const res of frameworkResponses) {
			if (res.ok) {
				const fw = await res.json();
				frameworkGroupsMap[fw.id] = fw.implementation_groups_definition || [];
			}
		}
	}

	return {
		complianceAssessments,
		riskAssessments,
		frameworkGroupsMap
	};
};
