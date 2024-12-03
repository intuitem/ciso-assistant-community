import { BASE_API_URL } from '$lib/utils/constants';
import {
	getModelInfo,
	urlParamModelForeignKeyFields,
	urlParamModelSelectFields
} from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	const URLModel = 'ebios-rm';
	const schema = modelSchema(URLModel);
	// const objectEndpoint = `${BASE_API_URL}/${URLModel}/${event.params.id}/object/`;
	const object = {
        version: '1.0',
        status: '',
        authors: '',
        reviewers: '',
        observation: ''
    };

	const form = await superValidate(object, zod(schema), { errors: false });
	const model = getModelInfo(URLModel!);
	const foreignKeyFields = model.foreignKeyFields;
	const selectFields = model.selectFields;

	const foreignKeys: Record<string, any> = {};

	if (foreignKeyFields) {
		for (const keyField of foreignKeyFields) {
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			const response = await event.fetch(url);
			if (response.ok) {
				foreignKeys[keyField.field] = await response.json().then((data) => data.results);
			} else {
				console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
			}
		}
	}

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${URLModel}/${
				selectField.detail ? event.params.id + '/' : ''
			}${selectField.field}/`;
			const response = await event.fetch(url);
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
	}
	model.foreignKeys = foreignKeys;
	model.selectOptions = selectOptions;
	return { form, model, object, foreignKeys, selectOptions, URLModel };
};