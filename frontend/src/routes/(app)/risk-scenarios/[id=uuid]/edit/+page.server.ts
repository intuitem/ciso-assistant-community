import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { StrengthOfKnowledgeEntry, urlModel } from '$lib/utils/types';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'risk-scenarios';
	const schema = modelSchema(URLModel);
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	const scenario = await fetch(baseEndpoint).then((res) => res.json());
	const form = await superValidate(object, zod(schema), { errors: false });
	const model = getModelInfo(URLModel);
	const foreignKeyFields = model.foreignKeyFields;
	const selectFields = model.selectFields;

	const riskMatrix = await fetch(`${BASE_API_URL}/risk-matrices/${object.risk_matrix}/`)
		.then((res) => res.json())
		.then((res) => JSON.parse(res.json_definition));

	const foreignKeys: Record<string, any> = {};

	if (foreignKeyFields) {
		for (const keyField of foreignKeyFields) {
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

	const tables: Record<string, any> = {};

	for (const key of ['assets', 'applied-controls'] as urlModel[]) {
		const keyEndpoint = `${BASE_API_URL}/${key}/?risk_scenarios=${params.id}`;
		const response = await fetch(keyEndpoint);
		if (response.ok) {
			const data = await response.json().then((data) => data.results);

			const metaData = tableSourceMapper(data, ['id']);

			const bodyData = tableSourceMapper(data, listViewFields[key].body);

			const table: TableSource = {
				head: listViewFields[key].head,
				body: bodyData,
				meta: metaData
			};
			tables[key] = table;
		} else {
			console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
		}
	}

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${URLModel}/${selectField.field}/`;
			const response = await fetch(url);
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

	const probabilityChoicesEndpoint = `${baseEndpoint}probability/`;
	const probabilityChoices = await fetch(probabilityChoicesEndpoint)
		.then((res) => res.json())
		.then((data) =>
			Object.entries(data)
				.map(([key, value]) => ({
					label: value,
					value: parseInt(key)
				}))
				.sort((a, b) => a.value - b.value)
		);

	const impactChoicesEndpoint = `${baseEndpoint}impact/`;
	const impactChoices = await fetch(impactChoicesEndpoint)
		.then((res) => res.json())
		.then((data) =>
			Object.entries(data)
				.map(([key, value]) => ({
					label: value,
					value: parseInt(key)
				}))
				.sort((a, b) => a.value - b.value)
		);

	const treatmentChoicesEndpoint = `${BASE_API_URL}/${URLModel}/treatment/`;
	const qualificationChoicesEndpoint = `${BASE_API_URL}/${URLModel}/qualification/`;

	const [treatmentChoices, qualificationChoices] = await Promise.all([
		treatmentChoicesEndpoint,
		qualificationChoicesEndpoint
	].map(
		(endpoint) => fetch(endpoint)
			.then((res) => res.json())
			.then((data) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: key
				}))
			)
	));

	const strengthOfKnowledgeChoicesEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/strength_of_knowledge/`;
	const strengthOfKnowledgeChoices: Record<string, StrengthOfKnowledgeEntry> = await fetch(
		strengthOfKnowledgeChoicesEndpoint
	).then((res) => res.json());

	const measureCreateSchema = modelSchema('applied-controls');
	const initialData = {
		folder: scenario.project.folder.id
	};
	const measureCreateForm = await superValidate(initialData, zod(measureCreateSchema), {
		errors: false
	});

	const measureModel = getModelInfo('applied-controls');
	const measureSelectOptions: Record<string, any> = {};

	if (measureModel.selectFields) {
		for (const selectField of measureModel.selectFields) {
			const url = `${BASE_API_URL}/applied-controls/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				measureSelectOptions[selectField.field] = await response.json().then((data) =>
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

	const measureForeignKeys: Record<string, any> = {};

	if (measureModel.foreignKeyFields) {
		for (const keyField of measureModel.foreignKeyFields) {
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			const response = await fetch(url);
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
		scenario,
		riskMatrix,
		foreignKeys,
		selectOptions,
		URLModel,
		probabilityChoices,
		impactChoices,
		treatmentChoices,
		qualificationChoices,
		strengthOfKnowledgeChoices: strengthOfKnowledgeChoices,
		tables,
		measureModel,
		measureCreateForm
	};
};

export const actions: Actions = {
	updateRiskScenario: async (event) => {
		const URLModel = 'risk-scenarios';
		const schema = modelSchema(URLModel);
		const endpoint = `${BASE_API_URL}/${URLModel}/${event.params.id}/`;
		const form = await superValidate(event.request, zod(schema));

		if (!form.valid) {
			console.log(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form: form });
		}

		const modelVerboseName: string = urlParamModelVerboseName(URLModel);
		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({ object: modelVerboseName })
			},
			event
		);
		redirect(
			302,
			event.url.searchParams.get('/updateRiskScenario') ?? `/risk-scenarios/${event.params.id}`
		);
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

		const scenarioEndpoint = `${BASE_API_URL}/risk-scenarios/${event.params.id}/`;
		const scenario = await event.fetch(`${scenarioEndpoint}object`).then((res) => res.json());

		const measures = [...scenario.applied_controls, measure.id];

		const patchRequestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify({ applied_controls: measures })
		};

		const patchRes = await event.fetch(scenarioEndpoint, patchRequestInitOptions);
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
				message: m.successfullyUpdatedObject({ object: model })
			},
			event
		);
		return { form };
	}
};
