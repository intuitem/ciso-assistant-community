import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelForeignKeyFields } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo, urlModel } from '$lib/utils/types';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';
import { listViewFields } from '$lib/utils/table';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = 'stakeholders';
	const createSchema = modelSchema(URLModel);
	const initialData = {
		ebios_rm_study: params.id
	};
	const createForm = await superValidate(initialData, zod(createSchema), { errors: false });
	const model: ModelInfo = getModelInfo(URLModel);
	const foreignKeyFields = urlParamModelForeignKeyFields(URLModel);

	const selectOptions: Record<string, any> = {};
	if (model.selectFields) {
		await Promise.all(
			model.selectFields.map(async (selectField) => {
				const url = model.endpointUrl
					? `${BASE_API_URL}/${model.endpointUrl}/${selectField.field}`
					: `${BASE_API_URL}/${model.urlModel}/${selectField.field}`;
				const response = await fetch(url);
				if (!response.ok) {
					console.error(`Failed to fetch data from ${url}: ${response.statusText}`);
					return null;
				}
				const data = await response.json();
				if (data) {
					selectOptions[selectField.field] = Object.entries(data).map(([key, value]) => ({
						label: value,
						value: key
					}));
				}
			})
		);
	}
	model.selectOptions = selectOptions;

	const foreignKeys: Record<string, any> = {};

	for (const keyField of foreignKeyFields) {
		const model = getModelInfo(keyField.urlModel);
		const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
		const url = model.endpointUrl
			? `${BASE_API_URL}/${model.endpointUrl}/${queryParams}`
			: `${BASE_API_URL}/${model.urlModel}/${queryParams}`;
		const response = await fetch(url);
		if (response.ok) {
			foreignKeys[keyField.field] = await response.json().then((data) => data.results);
		} else {
			console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
		}
	}

	model['foreignKeys'] = foreignKeys;

	const endpoint = `${BASE_API_URL}/${model.endpointUrl}?ebios_rm_study=${params.id}`;
	const res = await fetch(endpoint);
	const data = await res.json().then((res) => res.results);

	const bodyData = tableSourceMapper(data, listViewFields[URLModel as urlModel].body);

	const headData: Record<string, string> = listViewFields[URLModel as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: bodyData,
		meta: data // metaData
	};

	const radarEndpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/ecosystem_chart_data/`;

	const radarRes = await fetch(radarEndpoint);
	const radar = await radarRes.json();

	return { createForm, deleteForm, model, URLModel, table, radar };
};

export const actions: Actions = {
	create: async (event) => {
		// const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: 'stakeholders',
			action: 'create'
			// redirectToWrittenObject: redirectToWrittenObject
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'stakeholders' });
	}
};
