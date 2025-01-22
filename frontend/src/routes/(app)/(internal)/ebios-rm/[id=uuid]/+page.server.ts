import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import {
	getModelInfo,
	urlParamModelForeignKeyFields,
	urlParamModelSelectFields
} from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { type Actions } from '@sveltejs/kit';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { z } from 'zod';

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
	const riskModel = getModelInfo('risk-assessments');
	const foreignKeyFields = urlParamModelForeignKeyFields(riskModel.urlModel);
	const selectFields = urlParamModelSelectFields(riskModel.urlModel);

	const foreignKeys: Record<string, any> = {};

	for (const keyField of foreignKeyFields) {
		const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
		const keyModel = getModelInfo(keyField.urlModel);
		const url = keyModel.endpointUrl
			? `${BASE_API_URL}/${keyModel.endpointUrl}/${queryParams}`
			: `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
		const response = await fetch(url);
		if (response.ok) {
			foreignKeys[keyField.field] = await response.json().then((data) => data.results);
		} else {
			console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
		}
	}

	riskModel['foreignKeys'] = foreignKeys;

	const selectOptions: Record<string, any> = {};

	for (const selectField of selectFields) {
		if (selectField.detail) continue;
		const url = riskModel.endpointUrl
			? `${BASE_API_URL}/${riskModel.endpointUrl}/${selectField.field}/`
			: `${BASE_API_URL}/${riskModel.urlModel}/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			selectOptions[selectField.field] = await response.json().then((data) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: selectField.valueType === 'number' ? parseInt(key) : key
				}))
			);
		} else {
			console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
		}
	}

	riskModel['selectOptions'] = selectOptions;

	return { createRiskAnalysisForm, riskModel };
};

export const actions: Actions = {
	create: async (event) => {
		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify({
				status: 'done',
				step: 1,
				workshop: 5
			})
		};

		const endpoint = `${BASE_API_URL}/ebios-rm/studies/${event.params.id}/workshop/5/step/1/`;
		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.text();
			console.error(response);
		}

		return defaultWriteFormAction({
			event,
			urlModel: 'risk-assessments',
			action: 'create',
			redirectToWrittenObject: true
		});
	},
	changeStepState: async (event) => {
		const formData = await event.request.formData();
		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({
			workshop: z.number(),
			step: z.number(),
			status: z.string()
		});

		const form = await superValidate(formData, zod(schema));

		const workshop = formData.get('workshop');
		const step = formData.get('step');

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		};

		const endpoint = `${BASE_API_URL}/ebios-rm/studies/${event.params.id}/workshop/${workshop}/step/${step}/`;
		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.text();
			console.error(response);
			return fail(400, { form });
		}

		return { success: true, form };
	}
};
