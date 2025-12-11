import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('policies'),
		id: event.params.id
	});

	// Validation flow form with preset data
	const validationFlowSchema = modelSchema('validation-flows');
	const validationFlowInitialData = {
		folder: detailData.data.folder?.id || detailData.data.folder,
		policies: [event.params.id],
		ref_id: ''
	};
	const validationFlowForm = await superValidate(
		validationFlowInitialData,
		zod(validationFlowSchema),
		{
			errors: false
		}
	);
	const validationFlowModel = getModelInfo('validation-flows');

	// Populate selectOptions for validation flow model
	const validationFlowSelectOptions: Record<string, any> = {};
	if (validationFlowModel.selectFields) {
		for (const selectField of validationFlowModel.selectFields) {
			const url = `${BASE_API_URL}/validation-flows/${selectField.field}/`;
			const response = await event.fetch(url);
			if (response.ok) {
				validationFlowSelectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}
	validationFlowModel.selectOptions = validationFlowSelectOptions;

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
