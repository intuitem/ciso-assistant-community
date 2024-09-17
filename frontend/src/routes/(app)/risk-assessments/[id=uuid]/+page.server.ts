import { safeTranslate } from '$lib/utils/i18n';
import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';

import * as m from '$paraglide/messages';
import { localItems, toCamelCase } from '$lib/utils/locales';

import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const formData = await request.formData();

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = formData.get('urlmodel');

		const createForm = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${urlModel}/`;

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
				const response = await res.json();
				console.log(response);
				if (response.non_field_errors) {
					setError(createForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: createForm });
			}
			const model: string = urlParamModelVerboseName(urlModel);
			// TODO: reference newly created object
			return message(
				createForm,
				m.successfullyCreatedObject({
					object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase()
				})
			);
		}
		return { createForm };
	},
	delete: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const deleteForm = await superValidate(formData, zod(schema));

		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/risk-scenarios/${id}/`;

		if (!deleteForm.valid) {
			return fail(400, { form: deleteForm });
		}

		if (formData.has('delete')) {
			const requestInitOptions: RequestInit = {
				method: 'DELETE'
			};
			const res = await fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response = await res.json();
				console.log(response);
				if (response.non_field_errors) {
					setError(deleteForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: deleteForm });
			}
			const model: string = urlParamModelVerboseName(params.model!);
			// TODO: reference object by name instead of id
			return message(
				deleteForm,
				m.successfullyDeletedObject({
					object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase()
				})
			);
		}
		return { deleteForm };
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
