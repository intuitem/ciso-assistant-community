import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'ebios-rm';
	const model: ModelInfo = getModelInfo(URLModel);

	const endpoint = model.endpointUrl
		? `${BASE_API_URL}/${model.endpointUrl}/${params.id}/`
		: `${BASE_API_URL}/${model.urlModel}/${params.id}/`;
	const res = await fetch(endpoint);
	const data = await res.json();

	const initialData = {
		risk_matrix: data.risk_matrix.id,
		ebios_rm_study: params.id
	};

	const createSchema = modelSchema('risk-assessments');
	const createRiskAnalysisForm = await superValidate(initialData, zod(createSchema), {
		errors: false
	});

	return { createRiskAnalysisForm, model: getModelInfo('risk-assessments') };
};

export const actions: Actions = {
	create: async (event) => {
		// const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: 'risk-assessments',
			action: 'create'
			// redirectToWrittenObject: redirectToWrittenObject
		});
	}
};
