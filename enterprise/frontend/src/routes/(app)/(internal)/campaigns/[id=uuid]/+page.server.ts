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
		model: getModelInfo('campaigns'),
		id: event.params.id
	});

	// Scope-aware subtitle: "Internal campaign" / "Third-party campaign"
	// instead of the generic model name (mirrors the CE generic detail route).
	const targetScope = detailData.data?.target_scope;
	if (targetScope === 'Internal' || targetScope === 'internal') {
		detailData.modelVerboseName = 'internalCampaign';
	} else if (targetScope === 'External' || targetScope === 'external') {
		detailData.modelVerboseName = 'externalCampaign';
	}

	// Fetch the metrics data
	const metricsData = await event
		.fetch(`${BASE_API_URL}/campaigns/${event.params.id}/metrics/`)
		.then((res) => res.json());

	// Return the original data with the metrics added
	return {
		...detailData,
		metrics: metricsData
	};
};
export const actions: Actions = {
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	}
};
