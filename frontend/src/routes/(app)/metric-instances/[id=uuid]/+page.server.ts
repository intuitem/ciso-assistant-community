import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// Add dependency for cache invalidation
	event.depends('metric-instance:samples');

	const detailData = await loadDetail({
		event,
		model: getModelInfo('metric-instances'),
		id: event.params.id
	});

	// Fetch custom metric samples for the chart
	const samplesEndpoint = `${BASE_API_URL}/metrology/custom-metric-samples/?metric_instance=${event.params.id}`;
	const samples = await fetchAllPages(event.fetch, samplesEndpoint).catch(() => []);

	return {
		...detailData,
		samples
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
