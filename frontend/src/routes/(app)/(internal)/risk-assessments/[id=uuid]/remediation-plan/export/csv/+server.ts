import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/treatment_plan_csv/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the CSV file');
	}

	const fileName = `TP-${params.id}-${new Date().toISOString()}.csv`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/csv',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
