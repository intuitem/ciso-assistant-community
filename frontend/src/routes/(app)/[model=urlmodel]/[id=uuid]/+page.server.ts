import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';

import { localItems, toCamelCase } from '$lib/utils/locales';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';

import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = formData.get('urlmodel');

		const createForm = await superValidate(formData, zod(schema));

		if (!createForm.valid) {
			console.log(createForm.errors);
			return fail(400, { form: createForm });
		}

		const endpoint = `${BASE_API_URL}/${urlModel}/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(createForm.data)
		};

		const fileFields = Object.fromEntries(
			Object.entries(createForm.data).filter(([, value]) => value instanceof File)
		);

		Object.keys(fileFields).forEach((key) => {
			createForm.data[key] = undefined;
		});

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error(response);
			if (response.warning) {
				setFlash({ type: 'warning', message: response.warning }, event);
				return { createForm };
			}
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return { createForm };
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(createForm, key, value);
			});
			return fail(400, { form: createForm });
		}

		const createdObject = await res.json();

		if (fileFields.length > 0) {
			for (const [, file] of Object.entries(fileFields)) {
				if (file.size <= 0) {
					continue;
				}
				const fileUploadEndpoint = `${BASE_API_URL}/${urlModel}/${createdObject.id}/upload/`;
				const fileUploadRequestInitOptions: RequestInit = {
					headers: {
						'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
					},
					method: 'POST',
					body: file
				};
				const fileUploadRes = await event.fetch(fileUploadEndpoint, fileUploadRequestInitOptions);
				if (!fileUploadRes.ok) {
					const response = await fileUploadRes.json();
					console.error(response);
					if (response.non_field_errors) {
						setError(createForm, 'non_field_errors', response.non_field_errors);
					}
					return fail(400, { form: createForm });
				}
			}
		}

		const modelVerboseName: string = urlParamModelVerboseName(urlModel);

		if (modelVerboseName === 'User') {
			setFlash(
				{
					type: 'success',
					message: m.successfullyCreatedObject({
						object: localItems(languageTag())[toCamelCase(modelVerboseName)].toLowerCase()
					})
				},
				event
			);
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({
					object: localItems(languageTag())[toCamelCase(modelVerboseName)].toLowerCase()
				})
			},
			event
		);
		return { createForm };
	},
	delete: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const deleteForm = await superValidate(formData, zod(schema));

		const urlmodel = deleteForm.data.urlmodel;
		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/`;

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
					object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase()
				})
			);
		}
		return { deleteForm };
	},
	reject: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const rejectForm = await superValidate(formData, zod(schema));

		const urlmodel = rejectForm.data.urlmodel;
		const id = rejectForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/reject/`;

		if (!rejectForm.valid) {
			return fail(400, { form: rejectForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(rejectForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: rejectForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			rejectForm,
			m.successfullyRejectedObject({
				object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(),
				id: id
			})
		);
	},
	accept: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const acceptForm = await superValidate(formData, zod(schema));

		const urlmodel = acceptForm.data.urlmodel;
		const id = acceptForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/accept/`;

		if (!acceptForm.valid) {
			return fail(400, { form: acceptForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(acceptForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: acceptForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			acceptForm,
			m.successfullyValidatedObject({
				object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(),
				id: id
			})
		);
	},
	revoke: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const revokeForm = await superValidate(formData, zod(schema));

		const urlmodel = revokeForm.data.urlmodel;
		const id = revokeForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/revoke/`;

		if (!revokeForm.valid) {
			return fail(400, { form: revokeForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(revokeForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: revokeForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			revokeForm,
			m.successfullyRevokedObject({
				object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(),
				id: id
			})
		);
	}
};
