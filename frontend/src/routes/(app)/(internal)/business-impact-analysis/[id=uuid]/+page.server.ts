import { getModelInfo } from '$lib/utils/crud';
import { loadDetail, loadValidationFlowFormData } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('business-impact-analysis'),
		id: event.params.id
	});

	const metricsData = await event
		.fetch(`${BASE_API_URL}/resilience/business-impact-analysis/${event.params.id}/metrics/`)
		.then((res) => res.json());

	const { validationFlowForm, validationFlowModel } = await loadValidationFlowFormData({
		event,
		folderId: detailData.data.folder?.id || detailData.data.folder,
		targetField: 'business_impact_analysis',
		targetIds: [event.params.id]
	});

	return {
		...detailData,
		metrics: metricsData,
		validationFlowForm,
		validationFlowModel
	};
};
export const actions: Actions = {
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	}
};
