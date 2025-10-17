import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/resilience/asset-assessments/${params.id}/dependency-graph/`;

	const res = await fetch(endpoint);
	const graphData = await res.json();

	return {
		graphData
	};
};
