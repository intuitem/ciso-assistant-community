import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';

import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import { superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import type { LayoutServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';

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
				const table: TableSource = {
					head: listViewFields[e.urlModel].head,
					body: [],
					meta: []
				};

				const info = getModelInfo(e.urlModel);
				const urlModel = e.urlModel;

				const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
				const createSchema = modelSchema(e.urlModel);
				const createForm = await superValidate(zod(createSchema));

				const selectOptions: Record<string, any> = {};

				if (info.selectFields) {
					for (const selectField of info.selectFields) {
						const url = `${BASE_API_URL}/${urlModel}/${selectField.field}/`;
						const response = await fetch(url);
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
					}
				}
				relatedModels[e.urlModel] = {
					urlModel,
					info,
					table,
					deleteForm,
					createForm,
					selectOptions
				};
			})
		);
	}
	return { data, relatedModels, title: data.name };
};
