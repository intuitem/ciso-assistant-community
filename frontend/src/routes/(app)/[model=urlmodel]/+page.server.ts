import { safeTranslate } from '$lib/utils/i18n';
import { BASE_API_URL } from '$lib/utils/constants';
import {
	getModelInfo,
	urlParamModelForeignKeyFields,
	urlParamModelSelectFields,
	urlParamModelVerboseName
} from '$lib/utils/crud';
import { localItems, toCamelCase } from '$lib/utils/locales';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = params.model!;
	const createSchema = modelSchema(params.model!);
	const createForm = await superValidate(zod(createSchema));
	const model: ModelInfo = getModelInfo(params.model!);
	const foreignKeyFields = urlParamModelForeignKeyFields(params.model);
	const selectFields = urlParamModelSelectFields(params.model);

	const foreignKeys: Record<string, any> = {};

	for (const keyField of foreignKeyFields) {
		const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
		const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
		const response = await fetch(url);
		if (response.ok) {
			foreignKeys[keyField.field] = await response.json().then((data) => data.results);
		} else {
			console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
		}
	}

	model['foreignKeys'] = foreignKeys;

	const selectOptions: Record<string, any> = {};

	for (const selectField of selectFields) {
		if (selectField.detail) continue;
		const url = `${BASE_API_URL}/${params.model}/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			selectOptions[selectField.field] = await response.json().then((data) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: key
				}))
			);
		} else {
			console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
		}
	}

	model['selectOptions'] = selectOptions;

	return { createForm, deleteForm, model, URLModel };
};

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema(event.params.model!);
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const endpoint = `${BASE_API_URL}/${event.params.model}/`;

		const model = getModelInfo(event.params.model!);

		const fileFields: Record<string, File> = Object.fromEntries(
			Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
		);

		Object.keys(fileFields).forEach((key) => {
			form.data[key] = undefined;
		});

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error(response);
			if (response.warning) {
				setFlash({ type: 'warning', message: response.warning }, event);
				return { createForm: form };
			}
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return { createForm: form };
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form: form });
		}

		const createdObject = await res.json();

		if (fileFields) {
			for (const [, file] of Object.entries(fileFields)) {
				if (!file) continue;
				if (file.size <= 0) continue;
				const fileUploadEndpoint = `${BASE_API_URL}/${event.params.model}/${createdObject.id}/upload/`;
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
						setError(form, 'non_field_errors', response.non_field_errors);
					}
					return fail(400, { form: form });
				}
			}
		}

		const modelVerboseName: string = event.params.model
			? urlParamModelVerboseName(event.params.model)
			: '';
		// TODO: reference newly created object
		if (modelVerboseName === 'User') {
			setFlash(
				{
					type: 'success',
					message: m.successfullyCreatedObject({
						object: safeTranslate(modelVerboseName).toLowerCase()
					})
				},
				event
			);
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);
		return { createForm: form };
	},
	delete: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ id: z.string().uuid() });
		const deleteForm = await superValidate(formData, zod(schema));

		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/${event.params.model}/${id}/`;

		if (!deleteForm.valid) {
			console.log(deleteForm.errors);
			return fail(400, { form: deleteForm });
		}

		if (formData.has('delete')) {
			const requestInitOptions: RequestInit = {
				method: 'DELETE'
			};
			const res = await event.fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response = await res.json();
				console.log(response);
				if (response.error) {
					setFlash({ type: 'error', message: localItems()[response.error] }, event);
					return fail(403, { form: deleteForm });
				}
				if (response.non_field_errors) {
					setError(deleteForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: deleteForm });
			}
			const model: string = urlParamModelVerboseName(event.params.model!);
			// TODO: reference object by name instead of id
			setFlash(
				{
					type: 'success',
					message: m.successfullyDeletedObject({
						object: safeTranslate(model).toLowerCase()
					})
				},
				event
			);
		}
		return { deleteForm };
	}
};
