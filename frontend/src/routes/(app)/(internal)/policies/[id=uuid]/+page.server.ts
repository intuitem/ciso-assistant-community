import { getModelInfo } from '$lib/utils/crud';
import { loadDetail, loadValidationFlowFormData } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('policies'),
		id: event.params.id
	});

	const { validationFlowForm, validationFlowModel } = await loadValidationFlowFormData({
		event,
		folderId: detailData.data.folder?.id || detailData.data.folder,
		targetField: 'policies',
		targetIds: [event.params.id]
	});

	return {
		...detailData,
		validationFlowForm,
		validationFlowModel
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
