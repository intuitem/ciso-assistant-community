import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import { localItems, toCamelCase } from '$lib/utils/locales';
import { safeTranslate } from '$lib/utils/i18n';
import * as m from '$paraglide/messages';

import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const data = await loadDetail({
		event,
		model: getModelInfo(event.params.model),
		id: event.params.id
	});

	if (event.params.model === 'applied-controls') {
		const appliedControlSchema = modelSchema(event.params.model);
		const appliedControl = data.data;
		const initialDataDuplicate = {
			name: appliedControl.name,
			description: appliedControl.description
		};

		const appliedControlDuplicateForm = await superValidate(
			initialDataDuplicate,
			zod(appliedControlSchema),
			{
				errors: false
			}
		);

		data.duplicateForm = appliedControlDuplicateForm;
	}

	return data;
};

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

		const schema = modelSchema(event.params.model as string);

		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/duplicate/`;

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

		const modelVerboseName: string = urlParamModelVerboseName(event.params.model as string);
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
				object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase(),
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
				object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase(),
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
				object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase(),
				id: id
			})
		);
	}
};
