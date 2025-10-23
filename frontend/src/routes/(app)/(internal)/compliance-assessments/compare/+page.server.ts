import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, url }) => {
	const baseId = url.searchParams.get('base');
	const compareId = url.searchParams.get('compare');

	if (!baseId || !compareId) {
		throw error(400, 'Both base and compare audit IDs are required');
	}

	const URLModel = 'compliance-assessments';

	// Use the backend compare endpoint
	const comparisonEndpoint = `${BASE_API_URL}/${URLModel}/${baseId}/compare/?compare_id=${compareId}`;

	const comparisonData = await fetch(comparisonEndpoint).then((res) => {
		if (!res.ok) {
			if (res.status === 404) throw error(404, 'One or both audits not found');
			if (res.status === 403) throw error(403, 'Permission denied');
			if (res.status === 400) throw error(400, 'Invalid comparison request');
			throw error(500, 'Failed to load comparison data');
		}
		return res.json();
	});

	return {
		baseAudit: comparisonData.base,
		compareAudit: comparisonData.compare,
		title: `Compare: ${comparisonData.base.name} vs ${comparisonData.compare.name}`
	};
}) satisfies PageServerLoad;
