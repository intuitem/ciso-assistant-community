import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// Keep your existing loadDetail logic
	const detailData = await loadDetail({
		event,
		model: getModelInfo('asset-assessments'),
		id: event.params.id
	});

	const assetId = detailData.data.asset.id;
	const assetData = await event
		.fetch(`${BASE_API_URL}/assets/${assetId}/`)
		.then((res) => res.json());

	// Fetch the metrics data
	const metricsData = await event
		.fetch(`${BASE_API_URL}/resilience/asset-assessments/${event.params.id}/metrics/`)
		.then((res) => res.json());

	// Return the original data with the metrics added
	return {
		...detailData,
		asset: assetData,
		aaMetrics: metricsData
	};
};
export const actions: Actions = {
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	}
};
