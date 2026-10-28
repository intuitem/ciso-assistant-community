import { error } from '@sveltejs/kit';
import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/resilience/asset-assessments/${params.id}/dependency-graph/`;

	const res = await fetch(endpoint);
	if (!res.ok) error(res.status, 'Failed to load the dependency graph');
	const graphData = await res.json();

	return {
		graphData
	};
};
