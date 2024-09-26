import { handleErrorResponse, nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import type { Actions } from '@sveltejs/kit';
import { fail, redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'requirement-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const requirementAssessment = await res.json();

	const compliance_assessment_score = await fetch(
		`${BASE_API_URL}/compliance-assessments/${requirementAssessment.compliance_assessment.id}/global_score/`
	).then((res) => res.json());
	const requirement = await fetch(
		`${BASE_API_URL}/requirement-nodes/${requirementAssessment.requirement}/`
	).then((res) => res.json());
	const parentRequirementNodeEndpoint = `${BASE_API_URL}/requirement-nodes/?urn=${requirement.parent_urn}`;
	const parent = await fetch(parentRequirementNodeEndpoint)
		.then((res) => res.json())
		.then((res) => res.results[0]);

	const model = getModelInfo(URLModel);

	const object = { ...requirementAssessment };
	for (const key in object) {
		if (object[key] instanceof Object && 'id' in object[key]) {
			object[key] = object[key].id;
		}
	}

	const schema = modelSchema(URLModel);
	const form = await superValidate(object, zod(schema), { errors: true });

	const foreignKeys: Record<string, any> = {};

	if (model.foreignKeyFields) {
		for (const keyField of model.foreignKeyFields) {
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

	model.foreignKeys = foreignKeys;

	const selectOptions: Record<string, any> = {};

	if (model.selectFields) {
		for (const selectField of model.selectFields) {
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

	model['selectOptions'] = selectOptions;

	const measureCreateSchema = modelSchema('applied-controls');
	const initialData = {
		folder: requirementAssessment.folder.id
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

	measureModel['selectOptions'] = measureSelectOptions;

	const tables: Record<string, any> = {};

	for (const key of ['applied-controls', 'evidences'] as urlModel[]) {
		const keyEndpoint = `${BASE_API_URL}/${key}/?requirement_assessments=${params.id}`;
		const response = await fetch(keyEndpoint);
		if (response.ok) {
			const data = await response.json().then((data) => data.results);

			const bodyData = tableSourceMapper(data, listViewFields[key].body);

			const table: TableSource = {
				head: listViewFields[key].head,
				body: bodyData,
				meta: data
			};
			tables[key] = table;
		} else {
			console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
		}
	}

	const measureForeignKeys: Record<string, any> = {};

	if (measureModel.foreignKeyFields) {
		for (const keyField of measureModel.foreignKeyFields) {
			if (keyField.field === 'folder') {
				measureForeignKeys[keyField.field] = [requirementAssessment.folder];
				continue;
			}
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

	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateSchema = modelSchema('evidences');
	const evidenceInitialData = {
		requirement_assessments: [params.id],
		folder: requirementAssessment.folder.id
	};
	const evidenceCreateForm = await superValidate(evidenceInitialData, zod(evidenceCreateSchema), {
		errors: false
	});

	const evidenceSelectOptions: Record<string, any> = {};

	if (evidenceModel.selectFields) {
		for (const selectField of evidenceModel.selectFields) {
			const url = `${BASE_API_URL}/evidences/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				evidenceSelectOptions[selectField.field] = await response.json().then((data) =>
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

	evidenceModel['selectOptions'] = evidenceSelectOptions;

	const evidenceForeignKeys: Record<string, any> = {};

	if (evidenceModel.foreignKeyFields) {
		for (const keyField of evidenceModel.foreignKeyFields) {
			if (keyField.field === 'folder') {
				evidenceForeignKeys[keyField.field] = [requirementAssessment.folder];
				continue;
			}
			evidenceForeignKeys[keyField.field] = [];
		}
	}

	evidenceModel.foreignKeys = evidenceForeignKeys;

	return {
		URLModel,
		requirementAssessment,
		compliance_assessment_score,
		requirement,
		parent,
		model,
		form,
		measureCreateForm,
		measureModel,
		evidenceModel,
		evidenceCreateForm,
		tables
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateRequirementAssessment: async (event) => {
		const URLModel = 'requirement-assessments';
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

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const object = await response.json();
		const model: string = urlParamModelVerboseName(URLModel);
		setFlash({ type: 'success', message: m.successfullySavedObject({ object: model }) }, event);
		redirect(
			302,
			getSecureRedirect(event.url.searchParams.get('next')) ||
				`/compliance-assessments/${object.compliance_assessment}/`
		);
	},
	createAppliedControl: async (event) => {
		const URLModel = 'applied-controls';
		const schema = modelSchema(URLModel);
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

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const measure = await response.json();

		const requirementAssessmentEndpoint = `${BASE_API_URL}/requirement-assessments/${event.params.id}/`;
		const requirementAssessment = await event
			.fetch(`${requirementAssessmentEndpoint}object`)
			.then((res) => res.json());

		const measures = [...requirementAssessment.applied_controls, measure.id];

		const patchRequestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify({ applied_controls: measures })
		};

		const patchRes = await event.fetch(requirementAssessmentEndpoint, patchRequestInitOptions);
		if (!patchRes.ok) return handleErrorResponse({ event, response: patchRes, form });

		const model: string = urlParamModelVerboseName(URLModel);
		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({ object: model })
			},
			event
		);
		return { form };
	},
	createEvidence: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	}
};
