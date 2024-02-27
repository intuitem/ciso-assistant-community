import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

import { modelSchema } from '$lib/utils/schemas';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { superValidate } from 'sveltekit-superforms/server';
import { z } from 'zod';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/risk-assessments/${params.id}/`;

	const risk_assessment = await fetch(endpoint).then((res) => res.json());
	const scenarios = await fetch(`${BASE_API_URL}/risk-scenarios/?risk_assessment=${params.id}`)
		.then((res) => res.json())
		.then((res) => res.results);

	const risk_matrix = await fetch(
		`${BASE_API_URL}/risk-matrices/${risk_assessment.risk_matrix.id}/`
	).then((res) => res.json());

	const scenariosTable: TableSource = {
		head: [
			'rid',
			'name',
			'threats',
			'existingMeasures',
			'currentLevel',
			'securityMeasures',
			'residualLevel'
		],
		body: tableSourceMapper(scenarios, [
			'rid',
			'name',
			'threats',
			'existing_measures',
			'current_level',
			'security_measures',
			'residual_level'
		]),
		meta: scenarios
	};

	risk_assessment.risk_scenarios = scenarios;
	risk_assessment.risk_matrix = risk_matrix;

	const deleteSchema = z.object({ id: z.string() });
	const scenarioDeleteForm = await superValidate(deleteSchema);

	const scenarioSchema = modelSchema('risk-scenarios');
	const scenarioCreateForm = await superValidate(scenarioSchema);

	const scenarioModel = getModelInfo('risk-scenarios');

	return { risk_assessment, scenarioModel, scenariosTable, scenarioDeleteForm, scenarioCreateForm };
};
