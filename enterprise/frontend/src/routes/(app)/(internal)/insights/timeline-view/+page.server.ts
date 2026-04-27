import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

async function fetchAll(fetch: typeof globalThis.fetch, endpoint: string) {
	const res = await fetch(`${BASE_API_URL}/${endpoint}/`);
	if (!res.ok) return [];
	const data = await res.json();
	return data.results ?? data;
}

export const load: PageServerLoad = async ({ fetch }) => {
	// Folders are lightweight — await them so the page shell renders immediately
	const folders = await fetchAll(fetch, 'folders');

	// Stream the heavy data as a promise so the page can show a spinner
	const ganttData = Promise.all([
		fetchAll(fetch, 'applied-controls'),
		fetchAll(fetch, 'compliance-assessments'),
		fetchAll(fetch, 'risk-assessments'),
		fetchAll(fetch, 'business-impact-analysis'),
		fetchAll(fetch, 'findings-assessments'),
		fetchAll(fetch, 'security-exceptions')
	]).then(
		([
			appliedControls,
			complianceAssessments,
			riskAssessments,
			businessImpactAnalyses,
			findingsAssessments,
			securityExceptions
		]) => ({
			appliedControls,
			complianceAssessments,
			riskAssessments,
			businessImpactAnalyses,
			findingsAssessments,
			securityExceptions
		})
	);

	return {
		folders,
		ganttData
	};
};
