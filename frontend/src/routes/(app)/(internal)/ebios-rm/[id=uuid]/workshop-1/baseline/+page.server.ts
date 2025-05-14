import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { ModelInfo, urlModel } from '$lib/utils/types';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = 'compliance-assessments';
	const createSchema = modelSchema(URLModel);
	const updateSchema = modelSchema('ebios-rm');
	const initialData = {
		ebios_rm_studies: [params.id]
	};
	const updatedModel: ModelInfo = getModelInfo('ebios-rm');
	const createForm = await superValidate(initialData, zod(createSchema), { errors: false });
	const objectEndpoint = `${BASE_API_URL}/${updatedModel.endpointUrl}/${params.id}/object/`;
	const objectResponse = await fetch(objectEndpoint);
	const object = await objectResponse.json();
	const updateForm = await superValidate(object, zod(updateSchema), { errors: false });
	const model: ModelInfo = getModelInfo(URLModel);
	const selectFields = model.selectFields;

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${URLModel}/${
				selectField.detail ? params.id + '/' : ''
			}${selectField.field}/`;
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
	}

	model['selectOptions'] = selectOptions;

	const headData: Record<string, string> = listViewFields[URLModel as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return { createForm, deleteForm, model, URLModel, table, updateForm, updatedModel, object };
};

export const actions: Actions = {
	create: async (event) => {
		// const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: 'compliance-assessments',
			action: 'create'
			// redirectToWrittenObject: redirectToWrittenObject
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'compliance-assessments' });
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'ebios-rm', action: 'edit' });
	}
};
