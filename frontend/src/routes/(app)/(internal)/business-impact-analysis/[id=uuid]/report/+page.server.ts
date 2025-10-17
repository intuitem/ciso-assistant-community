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

	// Fetch asset assessments with full details
	const assetsResponse = await fetch(
		`${BASE_API_URL}/resilience/asset-assessments/?bia=${params.id}`
	);
	const assetsData = await assetsResponse.json();
	const assetAssessments = assetsData.results || [];

	// Fetch full asset details with comparisons for each asset assessment
	const assetsWithDetails = await Promise.all(
		assetAssessments.map(async (assetAssessment: any) => {
			const assetResponse = await fetch(`${BASE_API_URL}/assets/${assetAssessment.asset.id}/`);
			const assetDetails = await assetResponse.json();
			return {
				...assetAssessment,
				asset: assetDetails
			};
		})
	);

	// Sort by asset name
	assetsWithDetails.sort((a, b) => a.asset.name.localeCompare(b.asset.name));

	// Collect all unique applied controls from asset assessments
	const allControls = new Map();
	assetAssessments.forEach((aa: any) => {
		aa.associated_controls?.forEach((control: any) => {
			if (!allControls.has(control.id)) {
				allControls.set(control.id, control);
			}
		});
	});

	return {
		bia,
		timelineData,
		metrics,
		assets: assetsWithDetails,
		appliedControls: Array.from(allControls.values())
	};
};
