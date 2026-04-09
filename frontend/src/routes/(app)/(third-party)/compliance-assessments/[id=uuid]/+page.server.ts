import { nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadValidationFlowFormData } from '$lib/utils/load';
import { ComplianceAssessmentSchema } from '$lib/utils/schemas';
import { error, redirect, type Actions } from '@sveltejs/kit';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch, params, cookies, locals }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${endpoint}object/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		if (res.status === 404) {
			// Check if focus mode is active
			const focusFolderId = cookies.get('focus_folder_id');
			const focusModeEnabled = locals.featureflags?.focus_mode ?? false;
			const isFocusModeActive = focusFolderId && focusModeEnabled;

			const message = isFocusModeActive
				? m.objectNotReachableFromCurrentFocus()
				: m.objectNotFound();
			setFlash({ type: 'warning', message }, cookies);
			throw redirect(302, '/compliance-assessments');
		}
		throw error(res.status, res.statusText || 'Failed to load compliance assessment');
	}
	const compliance_assessment = await res.json();

	const auditModel = getModelInfo('compliance-assessments');
	const selectOptions: Record<string, any> = {};

	// Parallelize ALL independent API calls + form validation in a single batch.
	// Use BASE_API_URL for frameworks/ to avoid triggering a SvelteKit layout reload.
	const selectFieldPromises = (auditModel.selectFields || []).map(async (selectField) => {
		const url = `${BASE_API_URL}/compliance-assessments/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			const data = await response.json();
			selectOptions[selectField.field] = Object.entries(data).map(([key, value]) => ({
				label: value,
				value: selectField.valueType === 'number' ? parseInt(key) : key
			}));
		} else {
			console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
		}
	});

	const [
		object,
		tree,
		compliance_assessment_donut_values,
		global_score,
		threats,
		frameworksMappings,
		auditCreateForm,
		auditCloneForm,
		form,
		{ validationFlowForm }
	] = await Promise.all([
		fetch(objectEndpoint).then((res) => res.json()),
		fetch(`${endpoint}tree/`).then((res) => res.json()),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/donut_data/`).then((res) => res.json()),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/global_score/`).then((res) => res.json()),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/threats_metrics/`).then((res) => res.json()),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/frameworks/`).then((res) => res.json()),
		superValidate({ baseline: compliance_assessment.id }, zod(ComplianceAssessmentSchema), {
			errors: false
		}),
		superValidate(
			{
				baseline: compliance_assessment.id,
				framework: compliance_assessment.framework?.id,
				perimeter: compliance_assessment.perimeter?.id
			},
			zod(ComplianceAssessmentSchema),
			{ errors: false }
		),
		superValidate(zod(z.object({ id: z.string().uuid() }))),
		loadValidationFlowFormData({
			event: { fetch },
			folderId: compliance_assessment.folder.id,
			targetField: 'compliance_assessments',
			targetIds: [params.id]
		}),
		...selectFieldPromises
	]);

	auditModel.selectOptions = selectOptions;

	return {
		URLModel,
		compliance_assessment,
		auditCreateForm,
		auditCloneForm,
		auditModel,
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
