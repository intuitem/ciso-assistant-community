import { superValidate } from 'sveltekit-superforms';
import type { LayoutServerLoad } from './$types';
import { getSecureRedirect } from '$lib/utils/helpers';
import { redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import * as m from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

export const load: LayoutServerLoad = async (event) => {
	const URLModel = event.params.model!;
	const schema = modelSchema(event.params.model);
	const objectEndpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/object/`;
	const object = await event.fetch(objectEndpoint).then((res) => res.json());
	const form = await superValidate(object, zod(schema), { errors: false });
	const model = getModelInfo(event.params.model!);
	const foreignKeyFields = model.foreignKeyFields;
	const selectFields = model.selectFields;

	const foreignKeys: Record<string, any> = {};

	if (model.urlModel === 'risk-acceptances') {
		const riskAcceptance = await event
			.fetch(`${BASE_API_URL}/${event.params.model}/${event.params.id}/`)
			.then((res) => res.json());
		if (['Accepted', 'Rejected', 'Revoked'].includes(riskAcceptance.state)) {
			console.log("The state of risk acceptance doesn't allow it to be edited");
			setFlash(
				{
					type: 'error',
					message: m.riskAcceptanceStateDoesntAllowEdit({ riskAcceptance: riskAcceptance.name })
				},
				event
			);
			throw redirect(
				302,
				getSecureRedirect(event.url.searchParams.get('next')) ||
					`/${model.urlModel}/${riskAcceptance.id}`
			);
		}
	}

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
			const url = `${BASE_API_URL}/${event.params.model}/${
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
