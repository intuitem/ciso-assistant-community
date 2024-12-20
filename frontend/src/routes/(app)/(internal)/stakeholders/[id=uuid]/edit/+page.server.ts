import { type Actions } from '@sveltejs/kit';

import { defaultWriteFormAction } from '$lib/utils/actions';
import { fail, setError, superValidate } from 'sveltekit-superforms';
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
	const URLModel = 'stakeholders';
	const schema = modelSchema(URLModel);
	const model = getModelInfo(URLModel);
	const stakeholderEndpoint = `${BASE_API_URL}/ebios-rm/stakeholders/${event.params.id}/`;
	const stakeholder = await event.fetch(stakeholderEndpoint).then((res) => res.json());
	const object = await event.fetch(`${stakeholderEndpoint}object`).then((res) => res.json());

	const form = await superValidate(object, zod(schema), { errors: false });
	const foreignKeyFields = model.foreignKeyFields;
	const selectFields = model.selectFields;

	const foreignKeys: Record<string, any> = {};

	if (model.urlModel === 'risk-acceptances') {
		const riskAcceptance = await event
			.fetch(`${BASE_API_URL}/${URLModel}/${event.params.id}/`)
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
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			const keyModel = getModelInfo(keyField.urlModel);
			let url = keyModel.endpointUrl
				? `${BASE_API_URL}/${keyModel.endpointUrl}/${queryParams}`
				: `${BASE_API_URL}/${keyModel.urlModel}/${queryParams}`;
			if (keyModel.urlModel === 'assets' && URLModel === 'feared-events') {
				url = `${BASE_API_URL}/${keyModel.urlModel}/${queryParams}${object.ebios_rm_study}`;
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
			const url = `${BASE_API_URL}/${model.endpointUrl ?? URLModel}/${
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

	const measureCreateSchema = modelSchema('applied-controls');
	const initialData = {
		folder: stakeholder.folder.id
	};
	const measureCreateForm = await superValidate(initialData, zod(measureCreateSchema), {
		errors: false
	});

	const measureModel = getModelInfo('applied-controls');
	const measureSelectOptions: Record<string, any> = {};

	if (measureModel.selectFields) {
		for (const selectField of measureModel.selectFields) {
			const url = `${BASE_API_URL}/applied-controls/${selectField.field}/`;
			const response = await event.fetch(url);
			if (response.ok) {
				measureSelectOptions[selectField.field] = await response.json().then((data) =>
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

	const measureForeignKeys: Record<string, any> = {};

	if (measureModel.foreignKeyFields) {
		for (const keyField of measureModel.foreignKeyFields) {
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			const response = await event.fetch(url);
			if (response.ok) {
				measureForeignKeys[keyField.field] = await response.json().then((data) => data.results);
			} else {
				console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
			}
		}
	}

	measureModel.foreignKeys = measureForeignKeys;
	measureModel.selectOptions = measureSelectOptions;

	return {
		form,
		model,
		object,
		foreignKeys,
		selectOptions,
		URLModel,
		measureCreateForm,
		measureModel,
		title: m.edit()
	};
};

export const actions: Actions = {
	updateStakeholder: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'stakeholders', action: 'edit' });
	},
	createAppliedControl: async (event) => {
		const URLModel = 'applied-controls';
		const schema = modelSchema(URLModel);
		const model = getModelInfo(URLModel);
		const endpoint = `${BASE_API_URL}/${URLModel}/`;
		const form = await superValidate(event.request, zod(schema));

		if (!form.valid) {
			console.log(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: form });
		}

		const measure = await res.json();

		const stakeholderEndpoint = `${BASE_API_URL}/ebios-rm/stakeholders/${event.params.id}/`;
		const stakeholder = await event.fetch(`${stakeholderEndpoint}object`).then((res) => res.json());

		const measures = [...stakeholder.applied_controls, measure.id];

		const patchRequestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify({ applied_controls: measures })
		};

		const patchRes = await event.fetch(stakeholderEndpoint, patchRequestInitOptions);
		if (!patchRes.ok) {
			const response = await patchRes.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: form });
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({ object: model.verboseName.toLowerCase() })
			},
			event
		);
		return { form };
	}
};
