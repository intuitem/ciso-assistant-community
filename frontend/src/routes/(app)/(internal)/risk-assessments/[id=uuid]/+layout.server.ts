import { BASE_API_URL } from '$lib/utils/constants';
import { tableSourceMapper } from '$lib/utils/table';
import { getModelInfo } from '$lib/utils/crud';
import { loadValidationFlowFormData } from '$lib/utils/load';

import { modelSchema } from '$lib/utils/schemas';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import type { LayoutServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';
import { error, redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load: LayoutServerLoad = async ({ fetch, params, cookies, locals }) => {
	const endpoint = `${BASE_API_URL}/risk-assessments/${params.id}/`;

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
			throw redirect(302, '/risk-assessments');
		}
		throw error(res.status, res.statusText || 'Failed to load risk assessment');
	}
	const risk_assessment = await res.json();
	const scenarios = await fetch(`${BASE_API_URL}/risk-scenarios/?risk_assessment=${params.id}`)
		.then((res) => res.json())
		.then((res) => res.results);

	const risk_matrix = await fetch(
		`${BASE_API_URL}/risk-matrices/${risk_assessment.risk_matrix.id}/`
	).then((res) => res.json());

	const interface_settings = await fetch(`${BASE_API_URL}/settings/general/object/`).then((res) =>
		res.json()
	);

	const headFields = [
		'ref_id',
		'name',
		'threats',
		'inherentLevel',
		'existingControls',
		'currentLevel',
		'withinTolerance',
		'extraAppliedControls',
		'residualLevel'
	];

	const bodyFields = [
		'ref_id',
		'name',
		'threats',
		'inherent_level',
		'existing_applied_controls',
		'current_level',
		'within_tolerance',
		'applied_controls',
		'residual_level'
	];

	const headData: Record<string, string> = bodyFields.reduce((obj, key, index) => {
		obj[key] = headFields[index];
		return obj;
	}, {});

	const scenariosTable: TableSource = {
		head: headData,
		body: tableSourceMapper(scenarios, bodyFields),
		meta: scenarios
	};

	risk_assessment.risk_scenarios = scenarios;
	risk_assessment.risk_matrix = risk_matrix;

	const deleteSchema = z.object({ id: z.string() });
	const scenarioDeleteForm = await superValidate(zod(deleteSchema));

	const scenarioSchema = modelSchema('risk-scenarios');
	const initialData = {
		risk_assessment: params.id
	};
	const scenarioCreateForm = await superValidate(initialData, zod(scenarioSchema), {
		errors: false
	});

	const scenarioModel = getModelInfo('risk-scenarios');

	const selectOptions: Record<string, any> = {};

	if (scenarioModel.selectFields) {
		for (const selectField of scenarioModel.selectFields) {
			const url = `${BASE_API_URL}/risk-scenarios/${selectField.field}/`;
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

	scenarioModel.selectOptions = selectOptions;

	const riskAssessmentSchema = modelSchema('risk-assessments');

	const initialDataDuplicate = {
		name: risk_assessment.name,
		description: risk_assessment.description,
		version: risk_assessment.version
	};

	const riskAssessmentDuplicateForm = await superValidate(
		initialDataDuplicate,
		zod(riskAssessmentSchema),
		{
			errors: false
		}
	);

	const riskAssessmentModel = getModelInfo('risk-assessments');

	const { validationFlowForm, validationFlowModel } = await loadValidationFlowFormData({
		event: { fetch },
		folderId: risk_assessment.folder.id,
		targetField: 'risk_assessments',
		targetIds: [params.id]
	});

	return {
		risk_assessment,
		scenarioModel,
		scenariosTable,
		scenarioDeleteForm,
		scenarioCreateForm,
		riskAssessmentDuplicateForm,
		riskAssessmentModel,
		validationFlowForm,
		validationFlowModel,
		title: risk_assessment.str,
		useBubbles: interface_settings.interface_agg_scenario_matrix
	};
};
