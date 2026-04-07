import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

async function fetchAll(fetch: typeof globalThis.fetch, endpoint: string) {
	const res = await fetch(`${BASE_API_URL}/${endpoint}/?page_size=1000`);
	if (!res.ok) return [];
	const data = await res.json();
	return data.results ?? data;
}

export const load: PageServerLoad = async ({ fetch }) => {
	const [appliedControls, complianceAssessments, riskAssessments, folders] = await Promise.all([
		fetchAll(fetch, 'applied-controls'),
		fetchAll(fetch, 'compliance-assessments'),
		fetchAll(fetch, 'risk-assessments'),
		fetchAll(fetch, 'folders')
	]);

	return {
		appliedControls,
		complianceAssessments,
		riskAssessments,
		folders
	};
};
