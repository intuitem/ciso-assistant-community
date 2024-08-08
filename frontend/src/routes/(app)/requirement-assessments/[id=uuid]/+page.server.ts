import type { PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import { languageTag } from '$paraglide/runtime';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'requirement-assessments';
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const requirementAssessment = await fetch(baseEndpoint).then((res) => res.json());
	const complianceAssessmentScore = await fetch(
		`${BASE_API_URL}/compliance-assessments/${requirementAssessment.compliance_assessment.id}/global_score/`
	).then((res) => res.json());
	const requirement = await fetch(
		`${BASE_API_URL}/requirement-nodes/${requirementAssessment.requirement}/`
	).then((res) => res.json());
	const parentRequirementNodeEndpoint = `${BASE_API_URL}/requirement-nodes/?urn=${requirement.parent_urn}`;
	const parent = await fetch(parentRequirementNodeEndpoint)
		.then((res) => res.json())
		.then((res) => res.results[0]);

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

	return { requirementAssessment, complianceAssessmentScore, requirement, parent, tables };
}) satisfies PageServerLoad;
