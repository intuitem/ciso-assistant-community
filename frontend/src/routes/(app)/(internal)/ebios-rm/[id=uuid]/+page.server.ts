import { BASE_API_URL } from '$lib/utils/constants';
import { setFlash } from 'sveltekit-flash-message/server';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { getModelInfo, urlParamModelSelectFields, urlParamModelVerboseName } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { type Actions } from '@sveltejs/kit';
import { fail, message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
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
		ebios_rm_study: params.id,
		folder: data.folder.id
	};

	const createSchema = modelSchema('risk-assessments');
	const createRiskAnalysisForm = await superValidate(initialData, zod(createSchema), {
		errors: false
	});
	const riskModel = getModelInfo('risk-assessments');
	const selectFields = urlParamModelSelectFields(riskModel.urlModel);

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

	// Fetch sync preview if a risk assessment already exists
	let syncPreview = null;
	if (data.last_risk_assessment) {
		const previewEndpoint = `${BASE_API_URL}/risk-assessments/${data.last_risk_assessment.id}/sync_preview/`;
		const previewRes = await fetch(previewEndpoint);
		if (previewRes.ok) {
			syncPreview = await previewRes.json();
		}
	}

	return { createRiskAnalysisForm, riskModel, syncPreview };
};

export const actions: Actions = {
	create: async (event) => {
		// Mark workshop step as done
		const stepEndpoint = `${BASE_API_URL}/ebios-rm/studies/${event.params.id}/workshop/5/step/1/`;
		const stepRes = await event.fetch(stepEndpoint, {
			method: 'PATCH',
			body: JSON.stringify({ status: 'done', step: 1, workshop: 5 })
		});
		if (!stepRes.ok) {
			console.error(await stepRes.text());
		}

		// Create the risk assessment
		const formData = await event.request.formData();
		const schema = modelSchema('risk-assessments');
		const form = await superValidate(formData, zod(schema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const createRes = await event.fetch(`${BASE_API_URL}/risk-assessments/`, {
			method: 'POST',
			body: JSON.stringify(form.data)
		});
		if (!createRes.ok) {
			console.error(await createRes.text());
			return fail(createRes.status, { form });
		}

		const writtenObject = await createRes.json();

		// Auto-sync from EBIOS RM study
		await event.fetch(`${BASE_API_URL}/risk-assessments/${writtenObject.id}/sync_from_ebios_rm/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({})
		});

		// Flash success and let ModelForm handle the redirect (closes modal)
		const modelVerboseName = urlParamModelVerboseName('risk-assessments');
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);
		return message(form, { redirect: `/risk-assessments/${writtenObject.id}` });
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
