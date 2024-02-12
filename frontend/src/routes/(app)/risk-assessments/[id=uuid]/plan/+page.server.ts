import { BASE_API_URL } from '$lib/utils/constants';
import type { UUID } from 'crypto';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object`;

	const res = await fetch(endpoint);
	const risk_assessment = await res.json();
	const project = await fetch(`${BASE_API_URL}/projects/${risk_assessment.project}/object`).then(
		(res) => res.json()
	);
	const folder = await fetch(`${BASE_API_URL}/folders/${project.folder}/object`).then((res) =>
		res.json()
	);

	const scenariosEndpoint = `${BASE_API_URL}/risk-scenarios/?risk_assessment=${params.id}`;
	const scenariosRes = await fetch(scenariosEndpoint);
	const scenarios = await scenariosRes.json().then((res) => res.results);

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
	risk_assessment.project = project;
	risk_assessment.folder = folder;

	return { URLModel, risk_assessment };
}) satisfies PageServerLoad;
