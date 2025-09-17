import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { StrengthOfKnowledgeEntry } from '$lib/utils/types';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'risk-scenarios';
	const schema = modelSchema(URLModel);
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	const scenario = await fetch(baseEndpoint).then((res) => res.json());
	const form = await superValidate(object, zod(schema), { errors: false });
	const model = getModelInfo(URLModel);
	const selectFields = model.selectFields;

	const riskMatrix = await fetch(`${BASE_API_URL}/risk-matrices/${object.risk_matrix}/`)
		.then((res) => res.json())
		.then((res) => JSON.parse(res.json_definition));

	const tables: Record<string, any> = {};

	await Promise.all(
		['assets', 'applied-controls', 'vulnerabilities'].map(async (key) => {
			const keyEndpoint = `${BASE_API_URL}/${key}/?risk_scenarios=${params.id}`;
			const response = await fetch(keyEndpoint);
			if (response.ok) {
				const table: TableSource = {
					head: listViewFields[key].head,
					body: [],
					meta: []
				};
				tables[key] = table;
			} else {
				console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
			}
		})
	);

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${URLModel}/${selectField.field}/`;
			const response = await fetch(url);
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
	const qualificationChoicesEndpoint = `${BASE_API_URL}/${URLModel}/qualifications/`;

	const [treatmentChoices, qualificationChoices] = await Promise.all(
		[treatmentChoicesEndpoint, qualificationChoicesEndpoint].map((endpoint) =>
			fetch(endpoint)
				.then((res) => res.json())
				.then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: key
					}))
				)
		)
	);

	const strengthOfKnowledgeChoicesEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/strength_of_knowledge/`;
	const strengthOfKnowledgeChoices: Record<string, StrengthOfKnowledgeEntry> = await fetch(
		strengthOfKnowledgeChoicesEndpoint
	).then((res) => res.json());

	const measureCreateSchema = modelSchema('applied-controls');
	const initialData = {
		folder: scenario.perimeter.folder.id
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
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}

	measureModel.selectOptions = measureSelectOptions;

	return {
		form,
		model,
		scenario,
		riskMatrix,
		selectOptions,
		URLModel,
		probabilityChoices,
		impactChoices,
		treatmentChoices,
		qualificationChoices,
		strengthOfKnowledgeChoices: strengthOfKnowledgeChoices,
		tables,
		measureModel,
		measureCreateForm,
		title: m.edit()
	};
};

export const actions: Actions = {
	updateRiskScenario: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'risk-scenarios', action: 'edit' });
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
			const response: Record<string, any> = await res.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, safeTranslate(value));
			});
			return fail(400, { form });
		}

		const measure = await res.json();

		const scenarioEndpoint = `${BASE_API_URL}/risk-scenarios/${event.params.id}/`;
		const scenario = await event.fetch(`${scenarioEndpoint}object`).then((res) => res.json());

		const field: string = event.url.searchParams.get('field') || 'applied_controls';

		const measures = [...scenario[field], measure.id];

		const patchRequestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify({ [field]: measures })
		};

		const patchRes = await event.fetch(scenarioEndpoint, patchRequestInitOptions);
		if (!patchRes.ok) {
			const response = await patchRes.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form });
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({ object: model.verboseName.toLowerCase() })
			},
			event
		);
		return { form, newControl: { field, appliedControl: measure.id } };
	}
};
