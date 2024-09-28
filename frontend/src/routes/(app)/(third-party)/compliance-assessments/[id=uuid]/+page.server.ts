import { nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { ComplianceAssessmentSchema } from '$lib/utils/schemas';
import { json, type Actions } from '@sveltejs/kit';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';

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

	const initialData = { baseline: compliance_assessment.id };
	const auditCreateForm = await superValidate(initialData, zod(ComplianceAssessmentSchema), {
		errors: false
	});

	const auditModel = getModelInfo('compliance-assessments');

	const foreignKeys: Record<string, any> = {};

	if (auditModel.foreignKeyFields) {
		for (const keyField of auditModel.foreignKeyFields) {
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			let url: string;
			if (keyField.urlModel === 'frameworks') {
				url = `${BASE_API_URL}/${keyField.urlModel}/${compliance_assessment.framework.id}/mappings/`;
			} else {
				url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			}
			const response = await fetch(url);
			if (response.ok) {
				foreignKeys[keyField.field] = await response.json().then((data) => data.results);
			} else {
				console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
			}
		}
	}

	const mappingSetsEndpoint = `${BASE_API_URL}/requirement-mapping-sets/?reference_framework=${compliance_assessment.framework.id}`;

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

	const form = await superValidate(zod(z.object({ id: z.string().uuid() })));

	return {
		URLModel,
		compliance_assessment,
		auditCreateForm,
		auditModel,
		object,
		tree,
		compliance_assessment_donut_values,
		global_score,
		form
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	createSuggestedControls: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({ id: z.string().uuid() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`/compliance-assessments/${event.params.id}/suggestions/applied-controls`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			}
		);
		if (response.ok) {
			setFlash(
				{
					type: 'success',
					message: m.createAppliedControlsFromSuggestionsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.createAppliedControlsFromSuggestionsError()
				},
				event
			);
		}
		return { form };
	}
};
