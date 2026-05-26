import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const [foldersRes, casRes, runsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`),
		fetch(`${BASE_API_URL}/compliance-assessments/`),
		fetch(`${BASE_API_URL}/chat/agent-runs/?kind=audit_prefill&ordering=-created_at`)
	]);
	const foldersData = await foldersRes.json();
	const casData = await casRes.json();
	const runsData = await runsRes.json();
	return {
		folders: foldersData.results ?? foldersData,
		complianceAssessments: casData.results ?? casData,
		runs: runsData.results ?? runsData
	};
}) satisfies PageServerLoad;
