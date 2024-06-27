import { BASE_API_URL } from '$lib/utils/constants';
import { ComplianceAssessmentSchema, modelSchema } from '$lib/utils/schemas';
import { message, setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { fail, type Actions } from '@sveltejs/kit';
import * as m from '$paraglide/messages';
import { localItems, toCamelCase } from '$lib/utils/locales';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${endpoint}object`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const object = await fetch(objectEndpoint).then((res) => res.json());

	const tree = await fetch(`${endpoint}tree/`).then((res) => res.json());

	const compliance_assessment_donut_values = await fetch(
		`${BASE_API_URL}/${URLModel}/${params.id}/donut_data/`
	).then((res) => res.json());

	const global_score = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/global_score/`).then(
		(res) => res.json()
	);
	
	const initialData = {
	};
	const auditCreateForm = await superValidate(initialData, zod(ComplianceAssessmentSchema), {
		errors: false
	});

	const auditModel = getModelInfo('compliance-assessments');

	const foreignKeys: Record<string, any> = {};

	if (auditModel.foreignKeyFields) {
		for (const keyField of auditModel.foreignKeyFields) {
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

	auditModel.foreignKeys = foreignKeys;

	const selectOptions: Record<string, any> = {};

	if (auditModel.selectFields) {
		for (const selectField of auditModel.selectFields) {
			const url = `${BASE_API_URL}/compliance-assessments/${selectField.field}/`;
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

	auditModel.selectOptions = selectOptions;

	return {
		URLModel,
		compliance_assessment,
		auditCreateForm,
		auditModel,
		object,
		tree,
		compliance_assessment_donut_values,
		global_score
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const formData = await request.formData();

		const schema = modelSchema(formData.get('urlmodel') as string);
		const urlModel = formData.get('urlmodel');

		const createForm = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${urlModel}/`;

		if (!createForm.valid) {
			console.log(createForm.errors);
			return fail(400, { form: createForm });
		}

		if (formData) {
			const requestInitOptions: RequestInit = {
				method: 'POST',
				body: JSON.stringify(createForm.data)
			};
			const res = await fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response = await res.json();
				console.log(response);
				if (response.non_field_errors) {
					setError(createForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: createForm });
			}
			const model: string = urlParamModelVerboseName(urlModel);
			// TODO: reference newly created object
			return message(
				createForm,
				m.successfullyCreatedObject({
					object: localItems()[toCamelCase(model.toLowerCase())].toLowerCase()
				})
			);
		}
		return { createForm };
	}
};
