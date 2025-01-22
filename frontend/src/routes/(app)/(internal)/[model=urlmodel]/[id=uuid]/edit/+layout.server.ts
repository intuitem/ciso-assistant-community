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
	const model = getModelInfo(event.params.model!);
	const objectEndpoint = model.endpointUrl
		? `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/object/`
		: `${BASE_API_URL}/${event.params.model}/${event.params.id}/object/`;
	const object = await event.fetch(objectEndpoint).then((res) => res.json());

	const form = await superValidate(object, zod(schema), { errors: false });
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
					message: m.riskAcceptanceStateDoesntAllowEdit()
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
			let queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			if (keyField.detailUrlParams && Array.isArray(keyField.detailUrlParams)) {
				keyField.detailUrlParams.forEach((detailParam) => {
					const paramValue = object[detailParam]?.id;
					if (paramValue) {
						queryParams += queryParams
							? `&${detailParam}=${paramValue}`
							: `?${detailParam}=${paramValue}`;
					}
				});
			} // To prepare possible fetch for foreign keys with detail in generic views
			const keyModel = getModelInfo(keyField.urlModel);
			let url = keyModel.endpointUrl
				? `${BASE_API_URL}/${keyModel.endpointUrl}/${queryParams}`
				: `${BASE_API_URL}/${keyModel.urlModel}/${queryParams}`;
			if (
				['assets', 'attack-paths'].includes(keyModel.urlModel) &&
				['feared-events', 'operational-scenarios'].includes(event.params.model)
			) {
				url = `${BASE_API_URL}/${keyModel.endpointUrl || keyModel.urlModel}/${queryParams}${object.ebios_rm_study}`;
			}
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
			const url = `${BASE_API_URL}/${model.endpointUrl ?? event.params.model}/${
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
	model.foreignKeys = foreignKeys;
	model.selectOptions = selectOptions;
	return { form, model, object, foreignKeys, selectOptions, URLModel, title: m.edit() };
};
