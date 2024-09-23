import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

import * as m from '$paraglide/messages';

import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	duplicate: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = 'risk-assessments';

		const createForm = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${urlModel}/${params.id}/duplicate/`;

		if (!createForm.valid) {
			console.log(createForm.errors);
			return fail(400, { form: createForm });
		}

		if (formData) {
			const requestInitOptions: RequestInit = {
				method: 'POST',
				body: JSON.stringify(createForm.data)
			};
			const res = await fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response: Record<string, any> = await res.json();
				console.log(response);
				if (response.non_field_errors) {
					setError(createForm, 'non_field_errors', response.non_field_errors);
				}
				Object.entries(response).forEach(([key, value]) => {
					setError(createForm, key, value);
				});
				return fail(400, { form: createForm });
			}
			const modelVerboseName: string = urlParamModelVerboseName(urlModel);
			// TODO: reference newly created object
			setFlash(
				{
					type: 'success',
					message: m.successfullyDuplicateObject({
						object: safeTranslate(modelVerboseName).toLowerCase()
					})
				},
				cookies
			);
		}
		return { createForm };
	}
};
