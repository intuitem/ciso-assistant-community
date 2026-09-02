import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { formatSelectFieldData } from '$lib/utils/load';
import { modelSchema } from '$lib/utils/schemas';
import { headData } from '$lib/utils/table';
import type { StrengthOfKnowledgeEntry } from '$lib/utils/types';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
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
					head: headData(key),
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
				const responseData = await response.json();
				selectOptions[selectField.field] = formatSelectFieldData(responseData, selectField);
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
		folder: scenario.folder?.id ?? scenario.risk_assessment?.folder?.id
	};
	const measureCreateForm = await superValidate(initialData, zod(measureCreateSchema), {
		errors: false
	});

	const threatModelCreateForm = await superValidate(
		initialData,
		zod(modelSchema('threat-models')),
		{ errors: false }
	);
	const threatModelModel = getModelInfo('threat-models');

	const measureModel = getModelInfo('applied-controls');
	const measureSelectOptions: Record<string, any> = {};

	if (measureModel.selectFields) {
		for (const selectField of measureModel.selectFields) {
			const url = `${BASE_API_URL}/applied-controls/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				const responseData = await response.json();
				measureSelectOptions[selectField.field] = formatSelectFieldData(responseData, selectField);
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
		threatModelModel,
		threatModelCreateForm,
		title: m.edit()
	};
};

export const actions: Actions = {
	updateRiskScenario: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'risk-scenarios', action: 'edit' });
	},
	createThreatModel: async (event) => {
		const URLModel = 'threat-models';
		const model = getModelInfo(URLModel);
		const form = await superValidate(event.request, zod(modelSchema(URLModel)));

		if (!form.valid) {
			return fail(400, { form });
		}

		const res = await event.fetch(`${BASE_API_URL}/${URLModel}/`, {
			method: 'POST',
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error('server response:', response);
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, safeTranslate(value));
			});
			return fail(400, { form });
		}

		const threatModel = await res.json();
		const scenarioEndpoint = `${BASE_API_URL}/risk-scenarios/${event.params.id}/`;
		const scenario = await event.fetch(`${scenarioEndpoint}object/`).then((res) => res.json());

		const patchRes = await event.fetch(scenarioEndpoint, {
			method: 'PATCH',
			body: JSON.stringify({ threat_models: [...(scenario.threat_models ?? []), threatModel.id] })
		});
		if (!patchRes.ok) {
			console.error('server response:', await patchRes.json());
			return fail(400, { form });
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({ object: model.verboseName.toLowerCase() })
			},
			event
		);
		return { form, newThreatModel: threatModel.id };
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
		const scenario = await event.fetch(`${scenarioEndpoint}object/`).then((res) => res.json());

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
