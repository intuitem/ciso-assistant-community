import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'requirement-nodes';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/inspect_requirement/`;
	const response = await fetch(endpoint).then((res) => res.json());
	return {
		requirementAssessments: response.requirement_assessments,
		metrics: response.metrics
	};
}) satisfies PageServerLoad;
