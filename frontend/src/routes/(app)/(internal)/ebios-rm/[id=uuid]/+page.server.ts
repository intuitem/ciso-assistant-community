import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
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

	return { createRiskAnalysisForm, model: getModelInfo('risk-assessments') };
};

export const actions: Actions = {
	create: async (event) => {
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
