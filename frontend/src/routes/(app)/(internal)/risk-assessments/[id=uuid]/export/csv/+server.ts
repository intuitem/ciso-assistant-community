import { BASE_API_URL } from '#lib/utils/constants.js';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { hasSelection } from '#lib/utils/scenarioSelection.js';
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/risk_assessment_csv/${url.search}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the CSV file');
	}

	// A CSV has no cover page or extra sheet: a filtered one says so in its name.
	const scope = hasSelection(url.searchParams) ? '-selection' : '';
	const fileName = `RA-${params.id}${scope}-${new Date().toISOString()}.csv`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/csv',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
