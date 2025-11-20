import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

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

	// Validation flow form with preset data
	const validationFlowSchema = modelSchema('validation-flows');
	const validationFlowInitialData = {
		folder: detailData.data.folder?.id || detailData.data.folder,
		findings_assessments: [event.params.id],
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

	// Return the original data with the metrics added
	return {
		...detailData,
		findings_metrics: metricsData,
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
