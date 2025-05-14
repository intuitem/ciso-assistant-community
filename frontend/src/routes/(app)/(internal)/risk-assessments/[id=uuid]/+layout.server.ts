import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

import { modelSchema } from '$lib/utils/schemas';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import type { LayoutServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';

export const load: LayoutServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/risk-assessments/${params.id}/`;

	const risk_assessment = await fetch(endpoint).then((res) => res.json());
	const scenarios = await fetch(`${BASE_API_URL}/risk-scenarios/?risk_assessment=${params.id}`)
		.then((res) => res.json())
		.then((res) => res.results);

	const risk_matrix = await fetch(
		`${BASE_API_URL}/risk-matrices/${risk_assessment.risk_matrix.id}/`
	).then((res) => res.json());

	const interface_settings = await fetch(`${BASE_API_URL}/settings/general/object`).then((res) =>
		res.json()
	);

	const headFields = [
		'ref_id',
		'name',
		'threats',
		'existingControls',
		'currentLevel',
		'extraAppliedControls',
		'residualLevel'
	];

	const bodyFields = [
		'ref_id',
		'name',
		'threats',
		'existing_applied_controls',
		'current_level',
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

	return {
		risk_assessment,
		scenarioModel,
		scenariosTable,
		scenarioDeleteForm,
		scenarioCreateForm,
		riskAssessmentDuplicateForm,
		riskAssessmentModel,
		title: risk_assessment.str,
		useBubbles: interface_settings.interface_agg_scenario_matrix
	};
};
