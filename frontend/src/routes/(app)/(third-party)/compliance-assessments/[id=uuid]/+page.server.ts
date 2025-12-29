import { nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadValidationFlowFormData } from '$lib/utils/load';
import { ComplianceAssessmentSchema } from '$lib/utils/schemas';
import { type Actions } from '@sveltejs/kit';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${endpoint}object/`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();
	const folderId =
		typeof compliance_assessment.folder === 'string'
			? compliance_assessment.folder
			: compliance_assessment.folder?.id;
	const frameworkId =
		typeof compliance_assessment.framework === 'string'
			? compliance_assessment.framework
			: compliance_assessment.framework?.id;
	const perimeterId =
		typeof compliance_assessment.perimeter === 'string'
			? compliance_assessment.perimeter
			: compliance_assessment.perimeter?.id;
	const framework = frameworkId
		? await fetch(`${BASE_API_URL}/frameworks/${frameworkId}/`).then((res) =>
				res.ok ? res.json() : null
			)
		: null;

	const object = await fetch(objectEndpoint).then((res) => res.json());

	const tree = await fetch(`${endpoint}tree/`).then((res) => res.json());

	const compliance_assessment_donut_values = await fetch(
		`${BASE_API_URL}/${URLModel}/${params.id}/donut_data/`
	).then((res) => res.json());

	const global_score = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/global_score/`).then(
		(res) => res.json()
	);

	const threats = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/threats_metrics/`).then(
		(res) => res.json()
	);
	const initialData = { baseline: compliance_assessment.id };
	const auditCreateForm = await superValidate(initialData, zod(ComplianceAssessmentSchema), {
		errors: false
	});

	const cloneInitialData = {
		baseline: compliance_assessment.id,
		framework: frameworkId,
		perimeter: perimeterId ?? null
	};
	const auditCloneForm = await superValidate(cloneInitialData, zod(ComplianceAssessmentSchema), {
		errors: false
	});

	const auditModel = getModelInfo('compliance-assessments');

	const selectOptions: Record<string, any> = {};

	const frameworksMappings = await fetch(`/compliance-assessments/${params.id}/frameworks`).then(
		(res) => res.json()
	);

	if (auditModel.selectFields) {
		for (const selectField of auditModel.selectFields) {
			const url = `${BASE_API_URL}/compliance-assessments/${selectField.field}/`;
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

	auditModel.selectOptions = selectOptions;

	const form = await superValidate(zod(z.object({ id: z.string().uuid() })));

	const { validationFlowForm } = await loadValidationFlowFormData({
		event: { fetch },
		folderId,
		targetField: 'compliance_assessments',
		targetIds: [params.id]
	});

	return {
		URLModel,
		compliance_assessment,
		auditCreateForm,
		auditCloneForm,
		auditModel,
		framework,
		object,
		tree,
		compliance_assessment_donut_values,
		global_score,
		threats,
		form,
		frameworksMappings,
		validationFlowForm,
		title: compliance_assessment.name
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		const request = event.request.clone();
		const formData = await request.formData();
		const form = await superValidate(formData, zod(ComplianceAssessmentSchema));
		const redirectToWrittenObject = Boolean(form.data.baseline);
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject });
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
	},
	syncToActions: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({ id: z.string().uuid() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`${BASE_API_URL}/compliance-assessments/${event.params.id}/syncToActions/?dry_run=false`,
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
					message: m.syncToAppliedControlsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.syncToAppliedControlsError()
				},
				event
			);
		}
		return { form, message: { requirementAssessmentsSync: await response.json() } };
	}
};
