import { superValidate } from 'sveltekit-superforms';
import type { LayoutServerLoad } from './$types';
import { getSecureRedirect } from '$lib/utils/helpers';
import { redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

export const load: LayoutServerLoad = async (event) => {
	const URLModel = event.params.model!;
	const schema = modelSchema(event.params.model);
	const objectEndpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/object/`;
	const object = await event.fetch(objectEndpoint).then((res) => res.json());
	const form = await superValidate(object, zod(schema), { errors: false });
	const model = getModelInfo(event.params.model!);
	const selectFields = model.selectFields;

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
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}
	model.selectOptions = selectOptions;

	return { form, model, object, selectOptions, URLModel };
};
