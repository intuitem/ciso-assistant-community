import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import {
	getModelInfo,
	urlParamModelForeignKeyFields,
	urlParamModelSelectFields
} from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { type Actions } from '@sveltejs/kit';
import { fail, superValidate, withFiles, setError, message } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = params.model!;
	const createSchema = modelSchema(params.model!);
	const createForm = await superValidate(zod(createSchema));
	const model: ModelInfo = getModelInfo(params.model!);
	const selectFields = urlParamModelSelectFields(params.model);

	const selectOptions: Record<string, any> = {};

	for (const selectField of selectFields) {
		if (selectField.detail) continue;
		const url = model.endpointUrl
			? `${BASE_API_URL}/${model.endpointUrl}/${selectField.field}/`
			: `${BASE_API_URL}/${params.model}/${selectField.field}/`;
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

	model['selectOptions'] = selectOptions;

	if (model.urlModel === 'folders') {
		const folderImportForm = await superValidate(zod(modelSchema('folders-import')), {
			errors: false
		});
		model['folderImportForm'] = folderImportForm;
		model['folderImportModel'] = { urlModel: 'folders-import' };
	}

	return { createForm, deleteForm, model, URLModel };
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: event.params.model!,
			action: 'create',
			redirectToWrittenObject: redirectToWrittenObject
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: event.params.model! });
	},
	importFolder: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(modelSchema('folders-import')));
		if (!form.valid) {
			return fail(400, withFiles({ form }));
		}

		const { file } = Object.fromEntries(formData) as { file: File };

		const endpoint = `${BASE_API_URL}/folders/import/${form.data.load_missing_libraries ? '?load_missing_libraries=true' : ''}`;

		const response = await event.fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Disposition': `attachment; filename="${file.name}"`,
				'Content-Type': file.type,
				'X-CISOAssistantDomainName': form.data.name
			},
			body: file
		});
		const res = await response.json();

		if (!response.ok && res.missing_libraries) {
			setError(form, 'file', m.missingLibrariesInImport());
			for (let i = 0; i < res.missing_libraries.length; i += 2) {
				const urn = res.missing_libraries[i];
				const version = res.missing_libraries[i + 1];
				setError(form, 'non_field_errors', `${urn} v${version}`);
			}
			return message(form, { status: response.status });
		}

		if (!response.ok) {
			if (res.error) {
				setFlash({ type: 'error', message: safeTranslate(res.error) }, event);
				return withFiles({ form });
			}
			Object.entries(res).forEach(([key, value]) => {
				setError(form, key, safeTranslate(value));
			});
			return fail(400, withFiles({ form }));
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyImportedFolder()
			},
			event
		);

		return withFiles({ form });
	}
};
