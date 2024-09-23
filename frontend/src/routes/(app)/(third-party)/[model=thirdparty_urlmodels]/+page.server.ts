import { BASE_API_URL } from '$lib/utils/constants';
import {
	getModelInfo,
	urlParamModelForeignKeyFields,
	urlParamModelSelectFields,
	urlParamModelVerboseName
} from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { localItems } from '$lib/utils/locales';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';
import { defaultWriteFormAction } from '$lib/utils/actions';

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
		return defaultWriteFormAction({
			event,
			urlModel: event.params.model as string,
			action: 'create'
		});
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
