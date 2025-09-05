import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

import { m } from '$paraglide/messages';

import {
	handleErrorResponse,
	nestedDeleteFormAction,
	nestedWriteFormAction
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	duplicate: async (event) => {
		const formData = await event.request.formData();

		if (!formData) return;

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = 'risk-assessments';

		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${urlModel}/${event.params.id}/duplicate/`;

		if (!form.valid) {
			console.log(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};
		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const modelVerboseName: string = urlParamModelVerboseName(urlModel);
		setFlash(
			{
				type: 'success',
				message: m.successfullyDuplicateObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);

		return { form };
	},
	syncToActions: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		console.log(formData);

		const schema = z.object({ reset_residual: z.boolean().optional() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`${BASE_API_URL}/risk-assessments/${event.params.id}/sync-to-actions/?dry_run=false`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(form.data)
			}
		);
		if (response.ok) {
			setFlash(
				{
					type: 'success',
					message: m.syncToAppliedControlsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.syncToAppliedControlsError()
				},
				event
			);
		}
		const r = response.clone();
		console.log(await r.text());
		console.log(form.data);
		return { form, message: { riskScenarios: await response.json() } };
	}
};
