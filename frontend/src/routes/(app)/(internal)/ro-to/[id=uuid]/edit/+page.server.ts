import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad, Actions } from '../$types';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'ro-to';
	const model = getModelInfo(URLModel);
	const schema = modelSchema(URLModel);
	const objectEndpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/object/`;
	const objectResponse = await event.fetch(objectEndpoint);
	const object = await objectResponse.json();

	const form = await superValidate(object, zod(schema), { errors: false });
	const selectFields = model.selectFields;

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${model.endpointUrl}/${
				selectField.detail ? event.params.id + '/' : ''
			}${selectField.field}/`;
			const response = await event.fetch(url);
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
	model.selectOptions = selectOptions;
	return { form, model, object, selectOptions, URLModel, title: m.edit() };
};

export const actions: Actions = {
	default: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'ro-to', action: 'edit' });
	}
};
