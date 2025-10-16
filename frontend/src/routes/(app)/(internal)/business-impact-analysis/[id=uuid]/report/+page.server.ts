import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	// Fetch BIA details
	const biaResponse = await fetch(
		`${BASE_API_URL}/resilience/business-impact-analysis/${params.id}/`
	);
	const bia = await biaResponse.json();

	// Fetch timeline table data
	const timelineResponse = await fetch(
		`${BASE_API_URL}/resilience/business-impact-analysis/${params.id}/build-table/`
	);
	const timelineData = await timelineResponse.json();

	// Fetch metrics
	const metricsResponse = await fetch(
		`${BASE_API_URL}/resilience/business-impact-analysis/${params.id}/metrics/`
	);
	const metrics = await metricsResponse.json();

	// Fetch asset assessments to show included assets
	const assetsResponse = await fetch(
		`${BASE_API_URL}/resilience/asset-assessments/?bia=${params.id}`
	);
	const assetsData = await assetsResponse.json();

	return {
		bia,
		timelineData,
		metrics,
		assets: assetsData.results || []
	};
};
