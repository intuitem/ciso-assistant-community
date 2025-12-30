import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

async function fetchData(fetch: typeof globalThis.fetch, endpoint: string) {
	const res = await fetch(`${BASE_API_URL}/${endpoint}/`);
	const data = await res.json();
	return data.results || data;
}

export const load = (async ({ fetch }) => {
	const [
		appliedControls,
		taskNodes,
		complianceAssessments,
		riskAssessments,
		businessImpactAnalyses,
		organisationObjectives,
		findingsAssessments,
		folders
	] = await Promise.all([
		fetchData(fetch, 'applied-controls'),
		fetchData(fetch, 'task-nodes'),
		fetchData(fetch, 'compliance-assessments'),
		fetchData(fetch, 'risk-assessments'),
		fetchData(fetch, 'resilience/business-impact-analysis'),
		fetchData(fetch, 'organisation-objectives'),
		fetchData(fetch, 'findings-assessments'),
		fetchData(fetch, 'folders')
	]);

	return {
		appliedControls,
		taskNodes,
		complianceAssessments,
		riskAssessments,
		businessImpactAnalyses,
		organisationObjectives,
		findingsAssessments,
		folders
	};
}) satisfies PageServerLoad;
