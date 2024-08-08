import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';

import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import { superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import type { LayoutServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';
import { languageTag } from '$paraglide/runtime';

export const load: LayoutServerLoad = async ({ fetch, params }) => {
	const URLModel: urlModel = 'risk-matrices';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	const model = getModelInfo(URLModel);
	const relatedModels: Record<string, any> = {};

	if (model.reverseForeignKeyFields) {
		await Promise.all(
			model.reverseForeignKeyFields.map(async (e) => {
				const relEndpoint = `${BASE_API_URL}/${e.urlModel}/?${e.field}=${params.id}`;
				const res = await fetch(relEndpoint);
				const data = await res.json().then((res) => res.results);

				const metaData = tableSourceMapper(data, ['id']);

				const bodyData = tableSourceMapper(data, listViewFields[e.urlModel].body);

				const table: TableSource = {
					head: listViewFields[e.urlModel].head,
					body: bodyData,
					meta: metaData
				};

				const info = getModelInfo(e.urlModel);
				const urlModel = e.urlModel;

				const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
				const createSchema = modelSchema(e.urlModel);
				const createForm = await superValidate(zod(createSchema));

				const foreignKeys: Record<string, any> = {};

				if (info.foreignKeyFields) {
					for (const keyField of info.foreignKeyFields) {
						const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
						const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
						const response = await fetch(url);
						if (response.ok) {
							foreignKeys[keyField.field] = await response.json().then((data) => data.results);
						} else {
							console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
						}
					}
				}

				const selectOptions: Record<string, any> = {};

				if (info.selectFields) {
					for (const selectField of info.selectFields) {
						const url = `${BASE_API_URL}/${urlModel}/${selectField.field}/`;
						const response = await fetch(url);
						if (response.ok) {
							selectOptions[selectField.field] = await response.json().then((data) =>
								Object.entries(data).map(([key, value]) => ({
									label: value,
									value: key
								}))
							);
						} else {
							console.error(
								`Failed to fetch data for ${selectField.field}: ${response.statusText}`
							);
						}
					}
				}
				relatedModels[e.urlModel] = {
					urlModel,
					info,
					table,
					deleteForm,
					createForm,
					foreignKeys,
					selectOptions
				};
			})
		);
	}
	return { data, relatedModels };
};
