import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	// Keep your existing loadDetail logic
	const detailData = await loadDetail({
		event,
		model: getModelInfo('findings-assessments'),
		id: event.params.id
	});

	// Fetch the metrics data
	const metricsData = await event
		.fetch(`${BASE_API_URL}/findings-assessments/${event.params.id}/metrics/`)
		.then((res) => res.json());

	// Return the original data with the metrics added
	return {
		...detailData,
		findings_metrics: metricsData
	};
};
