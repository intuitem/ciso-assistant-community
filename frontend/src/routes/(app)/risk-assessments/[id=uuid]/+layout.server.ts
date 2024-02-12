import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, type ModelMapEntry } from '$lib/utils/crud';

import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import { superValidate } from 'sveltekit-superforms/server';
import { z, type AnyZodObject } from 'zod';
import type { LayoutServerLoad } from './$types';
import type { UUID } from 'crypto';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import type { SuperValidated } from 'sveltekit-superforms';
import type { urlModel } from '$lib/utils/types';

export const load: LayoutServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/risk-assessments/${params.id}/`;

	const risk_assessment = await fetch(endpoint).then((res) => res.json());
	const scenarios = await fetch(`${BASE_API_URL}/risk-scenarios/?risk_assessment=${params.id}`)
		.then((res) => res.json())
		.then((res) => res.results);
	const scenariosFilter: string =
		'?' +
		scenarios.map((scenario: Record<string, any>) => `risk_scenarios=${scenario.id}`).join('&');

	const measures = await fetch(`${BASE_API_URL}/security-measures/${scenariosFilter}`).then((res) =>
		res.json().then((res) => {
			const sorted = res.results.sort((a: Record<string, any>, b: Record<string, any>) => {
				const dateA = new Date(a.created_at);
				const dateB = new Date(b.created_at);
				return dateA.getTime() - dateB.getTime();
			});
			return sorted;
		})
	);
	const risk_matrix = await fetch(
		`${BASE_API_URL}/risk-matrices/${risk_assessment.risk_matrix.id}/`
	).then((res) => res.json());

	// Create a lookup for measures based on their id
	const measureLookup: { [id: string]: Record<string, any> } = measures.reduce(
		(acc: Record<string, any>, measure: Record<string, any>) => {
			acc[measure.id] = measure;
			return acc;
		},
		{}
	);

	// Replace the measures' UUIDs in each scenario with the corresponding measure instances
	const transformedScenarios = scenarios.map((scenario: Record<string, any>) => ({
		...scenario,
		security_measures: scenario.security_measures.map((childId: UUID) => measureLookup[childId])
	}));

	risk_assessment.risk_scenarios = transformedScenarios;
	risk_assessment.risk_matrix = risk_matrix;

	type RelatedModel = {
		urlModel: urlModel;
		info: ModelMapEntry;
		table: TableSource;
		deleteForm: SuperValidated<AnyZodObject>;
		createForm: SuperValidated<AnyZodObject>;
		foreignKeys: Record<string, any>;
		selectOptions: Record<string, any>;
	};

	type RelatedModels = {
		[K in urlModel]: RelatedModel;
	};

	const model = getModelInfo('risk-assessments');
	const relatedModels = {} as RelatedModels;

	if (model.reverseForeignKeyFields) {
		await Promise.all(
			model.reverseForeignKeyFields.map(async (e) => {
				const relEndpoint = `${BASE_API_URL}/${e.urlModel}/?${e.field}=${params.id}`;
				const res = await fetch(relEndpoint);
				const data = await res.json().then((res) => res.results);

				const metaData = tableSourceMapper(data, ['id']);

				const bodyData = tableSourceMapper(data, listViewFields[e.urlModel].body);

				const table: TableSource = {
					head: listViewFields[e.urlModel].head,
					body: bodyData,
					meta: metaData
				};

				const info = getModelInfo(e.urlModel);
				const urlModel = e.urlModel;

				const deleteForm = await superValidate(z.object({ id: z.string().uuid() }));
				const createSchema = modelSchema(e.urlModel);
				const createForm = await superValidate(
					{ risk_assessment: risk_assessment.id },
					createSchema,
					{
						errors: false
					}
				);

				const foreignKeys: Record<string, any> = {};

				if (info.foreignKeyFields) {
					for (const keyField of info.foreignKeyFields) {
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

				const selectOptions: Record<string, any> = {};

				if (info.selectFields) {
					for (const selectField of info.selectFields) {
						const url = `${BASE_API_URL}/${urlModel}/${selectField.field}/`;
						const response = await fetch(url);
						if (response.ok) {
							selectOptions[selectField.field] = await response.json().then((data) =>
								Object.entries(data).map(([key, value]) => ({
									label: value,
									value: key
								}))
							);
						} else {
							console.error(
								`Failed to fetch data for ${selectField.field}: ${response.statusText}`
							);
						}
					}
				}
				relatedModels[e.urlModel] = {
					urlModel,
					info,
					table,
					deleteForm,
					createForm,
					foreignKeys,
					selectOptions
				};
			})
		);
	}

	return { risk_assessment, relatedModels };
};
