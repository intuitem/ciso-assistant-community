import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

import * as m from '$paraglide/messages';

import {
	handleErrorResponse,
	nestedDeleteFormAction,
	nestedWriteFormAction
} from '$lib/utils/actions';
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
	}
};
