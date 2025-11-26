import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('metric-instances'),
		id: event.params.id
	});

	// Fetch metric samples for the chart
	const samplesEndpoint = `${BASE_API_URL}/metrology/metric-samples/?metric_instance=${event.params.id}`;
	const samplesResponse = await event.fetch(samplesEndpoint);
	const samplesData = samplesResponse.ok ? await samplesResponse.json() : { results: [] };

	return {
		...detailData,
		samples: samplesData.results || []
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
