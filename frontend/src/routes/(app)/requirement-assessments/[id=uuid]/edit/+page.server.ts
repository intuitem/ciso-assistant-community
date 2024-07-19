import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { localItems, toCamelCase } from '$lib/utils/locales';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import type { Actions } from '@sveltejs/kit';
import { getSecureRedirect } from '$lib/utils/helpers';
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
			// const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			// const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			// const response = await fetch(url);
			// if (response.ok) {
			// 	evidenceForeignKeys[keyField.field] = await response.json().then((data) => data.results);
			// } else {
			// 	console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
			// }
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

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			if (response.score) {
				setError(form, 'score', response.score);
			}
			return fail(400, { form: form });
		}
		const object = await res.json();
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
		if (!patchRes.ok) {
			const response = await patchRes.json();
			console.error('server response:', response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: form });
		}

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
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema('evidences');
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const endpoint = `${BASE_API_URL}/evidences/`;

		const fileFields = Object.fromEntries(
			Object.entries(form.data).filter(([, value]) => value instanceof File)
		);

		Object.keys(fileFields).forEach((key) => {
			form.data[key] = undefined;
		});

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error(response);
			if (response.warning) {
				setFlash({ type: 'warning', message: response.warning }, event);
				return { createForm: form };
			}
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return { createForm: form };
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form: form });
		}

		const createdObject = await res.json();

		if (fileFields) {
			for (const [, file] of Object.entries(fileFields)) {
				if (file.size <= 0) {
					continue;
				}
				const fileUploadEndpoint = `${BASE_API_URL}/${'evidences'}/${createdObject.id}/upload/`;
				const fileUploadRequestInitOptions: RequestInit = {
					headers: {
						'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
					},
					method: 'POST',
					body: file
				};
				const fileUploadRes = await event.fetch(fileUploadEndpoint, fileUploadRequestInitOptions);
				if (!fileUploadRes.ok) {
					const response = await fileUploadRes.json();
					console.error(response);
					if (response.non_field_errors) {
						setError(form, 'non_field_errors', response.non_field_errors);
					}
					return fail(400, { form: form });
				}
			}
		}

		const modelVerboseName = 'evidences';
		// TODO: reference newly created object
		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({
					object: localItems()[toCamelCase(modelVerboseName)].toLowerCase()
				})
			},
			event
		);
		return { createForm: form };
	}
};
