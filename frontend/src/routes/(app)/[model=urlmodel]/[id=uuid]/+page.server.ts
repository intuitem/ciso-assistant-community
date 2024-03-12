import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';

import * as m from '$paraglide/messages';
import { localItems, toCamelCase } from '$lib/utils/locales';
import { languageTag } from '$paraglide/runtime';

import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms/server';
import { z } from 'zod';

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const formData = await request.formData();

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = formData.get('urlmodel');

		const createForm = await superValidate(formData, schema);

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
			const createdObject = await res.json();

			if (formData.has('attachment') && (formData.get('attachment') as File).size > 0) {
				const { attachment } = Object.fromEntries(formData) as { attachment: File };
				const attachmentEndpoint = `${BASE_API_URL}/${urlModel}/${createdObject.id}/upload/`;
				const attachmentRequestInitOptions: RequestInit = {
					headers: {
						'Content-Disposition': `attachment; filename=${encodeURIComponent(attachment.name)}`
					},
					method: 'POST',
					body: attachment
				};
				console.log(attachmentRequestInitOptions);
				const attachmentRes = await fetch(attachmentEndpoint, attachmentRequestInitOptions);
				if (!attachmentRes.ok) {
					const response = await attachmentRes.json();
					console.error(response);
					if (response.non_field_errors) {
						setError(createForm, 'non_field_errors', response.non_field_errors);
					}
					return fail(400, { form: createForm });
				}
			}

			const model: string = urlParamModelVerboseName(urlModel);
			if (model === 'User') {
				return message(
					createForm,
					m.successfullyCreatedUser()
				);
			}
			return message(createForm, m.successfullyCreatedObject({object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase()}));
		}
		return { createForm };
	},
	delete: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const deleteForm = await superValidate(formData, schema);

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
			return message(deleteForm, m.successfullyDeletedObject({object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase()}));
		}
		return { deleteForm };
	},
	reject: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const rejectForm = await superValidate(formData, schema);

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
		return message(rejectForm, m.successfullyRejectedObject({object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(), id: id}));
	},
	accept: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const acceptForm = await superValidate(formData, schema);

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
		return message(acceptForm, m.successfullyValidatedObject({object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(), id: id}));
	},
	revoke: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const revokeForm = await superValidate(formData, schema);

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
		return message(revokeForm, m.successfullyRevokedObject({object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(), id: id}));
	}
};
