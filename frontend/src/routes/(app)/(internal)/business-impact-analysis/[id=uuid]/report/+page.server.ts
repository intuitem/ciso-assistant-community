import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { error, type NumericRange } from '@sveltejs/kit';
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
	const assetAssessments = await fetchAllPages(
		fetch,
		`${BASE_API_URL}/resilience/asset-assessments/?bia=${params.id}`
	).catch(() => []);

	// Bulk-fetch full asset details instead of one request per assessment
	const assetDetailsById = new Map<string, any>();
	let offset = 0;
	let count = Infinity;
	while (assetDetailsById.size < count) {
		const res = await fetch(`${BASE_API_URL}/assets/full/?bia=${params.id}&offset=${offset}`);
		if (!res.ok) {
			error(res.status as NumericRange<400, 599>, 'Failed to load full asset details');
		}
		const data = await res.json();
		const items = data.results ?? [];
		if (items.length === 0) break;
		for (const asset of items) assetDetailsById.set(asset.id, asset);
		count = typeof data.count === 'number' ? data.count : items.length;
		offset += items.length;
	}

	const assetsWithDetails = assetAssessments.map((assetAssessment: any) => ({
		...assetAssessment,
		asset: assetDetailsById.get(assetAssessment.asset.id) ?? assetAssessment.asset
	}));

	// Sort by asset name
	assetsWithDetails.sort((a: any, b: any) => a.asset.name.localeCompare(b.asset.name));

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
