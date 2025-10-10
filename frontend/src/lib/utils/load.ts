import { BASE_API_URL, UUID_REGEX } from '$lib/utils/constants';
import { getModelInfo, type ModelMapEntry } from '$lib/utils/crud';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';

import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import type { SuperValidated } from 'sveltekit-superforms';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z, type AnyZodObject } from 'zod';
import { canPerformAction } from './access-control';

export const loadDetail = async ({ event, model, id }) => {
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? model.urlModel}/${id}/`;

	const res = await event.fetch(endpoint);
	const data = await res.json();

	type RelatedModel = {
		urlModel: urlModel;
		info: ModelMapEntry;
		table: TableSource;
		deleteForm: SuperValidated<AnyZodObject>;
		createForm: SuperValidated<AnyZodObject>;
		foreignKeys: Record<string, any>;
		selectOptions: Record<string, any>;
	};

	type RelatedModels = {
		[K in urlModel]: RelatedModel;
	};

	const form = await superValidate(zod(z.object({ id: z.string().uuid() })));

	const relatedModels = {} as RelatedModels;

	if (model.reverseForeignKeyFields) {
		const initialData = {};
		await Promise.all(
			model.reverseForeignKeyFields
				.filter(
					(m) =>
						!m?.folderPermsNeeded ||
						canPerformAction({
							user: event.locals.user,
							action: 'change',
							model: 'folder',
							domain:
								model.name === 'folder'
									? data.id
									: (data.folder?.id ?? data.folder ?? event.locals.user.root_folder_id)
						})
				)
				.map(async (e) => {
					if (
						e.urlModel === 'perimeters' &&
						model.urlModel === 'folders' &&
						data.content_type === 'GLOBAL'
					)
						return;
					const tableFieldsRef = listViewFields[e.urlModel];
					const tableFields = {
						head: [...tableFieldsRef.head],
						body: [...tableFieldsRef.body]
					};
					const index = tableFields.body.indexOf(e.field);
					if (index > -1) {
						tableFields.head.splice(index, 1);
						tableFields.body.splice(index, 1);
					}
					const headData: Record<string, string> = tableFields.body.reduce((obj, key, index) => {
						obj[key] = index < tableFields.head.length ? tableFields.head[index] : key;
						return obj;
					}, {});
					const table: TableSource = {
						head: headData,
						body: [],
						meta: []
					};

					const info = getModelInfo(e.urlModel);
					const urlModel = e.urlModel;

					const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
					const createSchema = modelSchema(e.urlModel);
					const fieldSchema = createSchema.shape[e.field];
					let isArrayField = false;

					if (fieldSchema) {
						let currentSchema = fieldSchema;
						while (
							currentSchema instanceof z.ZodOptional ||
							currentSchema instanceof z.ZodNullable
						) {
							currentSchema = currentSchema._def.innerType;
						}
						isArrayField = currentSchema instanceof z.ZodArray;
					}
					initialData[e.field] = isArrayField ? [data.id] : data.id;
					if (data.ebios_rm_study) {
						initialData['ebios_rm_study'] = data.ebios_rm_study.id;
					}
					if (data.folder) {
						if (!new RegExp(UUID_REGEX).test(data.folder) && !data?.folder?.id) {
							const objectEndpoint = `${endpoint}object/`;
							const objectResponse = await event.fetch(objectEndpoint);
							const objectData = await objectResponse.json();
							initialData['folder'] = objectData.folder;
						} else {
							initialData['folder'] = data?.folder?.id ?? data.folder;
						}
					}
					const createForm = await superValidate(initialData, zod(createSchema), { errors: false });

					const selectOptions: Record<string, any> = {};

					if (info.selectFields) {
						await Promise.all(
							info.selectFields.map(async (selectField) => {
								let url = `${BASE_API_URL}/${info.endpointUrl || info.urlModel}/${selectField.field}/`;
								if (selectField.formNestedField && selectField.detail === true) {
									url = `${BASE_API_URL}/${selectField.endpointUrl}/${initialData[selectField.formNestedField]}/${selectField.field}/`;
								}
								const response = await event.fetch(url);
								if (response.ok) {
									selectOptions[selectField.field] = await response.json().then((data) =>
										Object.entries(data).map(([key, value]) => ({
											label: value,
											value: selectField.valueType === 'number' ? parseInt(key) : key
										}))
									);
								} else {
									console.error(
										`Failed to fetch data for ${selectField.field}: ${response.statusText}`
									);
								}
							})
						);
					}
					relatedModels[e.urlModel] = {
						urlModel,
						info,
						table,
						deleteForm,
						createForm,
						selectOptions,
						initialData,
						disableCreate: e.disableCreate,
						disableDelete: e.disableDelete
					};
				})
		);
	}
	return {
		data,
		title: data.str || data.name || data.email || data.label || data.id,
		form,
		relatedModels,
		urlModel: model.urlModel as urlModel,
		model
	};
};
